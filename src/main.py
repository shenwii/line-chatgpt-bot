#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import openai
import textwrap
from urllib.parse import (
    urlencode,
    parse_qs
)
from database import Database
from settings import Settings
from command import Command
from fastapi import Request, FastAPI, HTTPException, Depends
from linebot.v3 import (
    WebhookParser
)
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    CarouselTemplate,
    CarouselColumn,
    PostbackAction
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    TextMessageContent
)
import logging

app_settings = Settings()

openai.api_key = app_settings.openai_api_key
openai.base_url = app_settings.openai_base_url

__db = Database(app_settings.mongo_uri, app_settings.database)

async def get_db():
    return __db

async def get_linebot_api():
    configuration = Configuration(
        access_token = app_settings.line_channel_access_token
    )
    async with AsyncApiClient(configuration) as api_client:
        yield AsyncMessagingApi(api_client)

async def get_openai_client():
    async with openai.AsyncOpenAI() as openai_client:
        yield openai_client

app = FastAPI()
command = Command()

async def handle_message(event = ..., linebot_api: AsyncMessagingApi = ..., db: Database = ..., openai_client: openai.AsyncOpenAI = ...):
    user_id = event.source.user_id
    user = await db.fetch_user(user_id, next(iter(app_settings.assistants)), next(iter(app_settings.models)))
    if not user["model"] in app_settings.models:
        await linebot_api.reply_message(
            ReplyMessageRequest(
                reply_token = event.reply_token,
                messages = [TextMessage(text=f"model is not exists: {user['model']}")]
            )
        )
        return
    if app_settings.models[user["model"]]["type"] == "chat":
        if not user["assistant"] in app_settings.assistants:
            await linebot_api.reply_message(
                ReplyMessageRequest(
                    reply_token = event.reply_token,
                    messages = [TextMessage(text=f"assistant is not exists: {user['assistant']}")]
                )
            )
            return
        conversation_history = user["conversation_history"][-app_settings.max_history:]
        if len(conversation_history) > 0 and type(conversation_history[-1]["content"]) == list:
            conversation_history[-1]["content"].append({"type": "input_text", "text": event.message.text})
        else:
            conversation_history.append({"role": "user", "content": event.message.text})
        completion = await openai_client.chat.completions.create(
            model = app_settings.models[user["model"]]["model"],
            messages = [{"role": "system", "content": app_settings.assistants[user["assistant"]]["instructions"]}]
                + conversation_history,
            **app_settings.models[user["model"]]["props"]
        )
        model_reply = completion.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": model_reply})
        await linebot_api.reply_message(
            ReplyMessageRequest(
                reply_token = event.reply_token,
                messages = [TextMessage(text=model_reply)]
            )
        )
        await db.update_user(user["_id"], {"$set": {"conversation_history": conversation_history}})

async def handle_action_select_model(event = ..., data = ..., linebot_api: AsyncMessagingApi = ..., db: Database = ..., openai_client: openai.AsyncOpenAI = ...):
    user_id = event.source.user_id
    user = await db.fetch_user(user_id, next(iter(app_settings.assistants)), next(iter(app_settings.models)))
    await db.update_user(user["_id"], {"$set": {"model": data["model"]}})
    await linebot_api.reply_message(
        ReplyMessageRequest(
            reply_token = event.reply_token,
            messages = [TextMessage(text=f"モデル {data['model']} が選択しました。")]
        )
    )

@app.post("/callback")
async def handle_callback(request: Request, linebot_api: AsyncMessagingApi = Depends(get_linebot_api), db: Database = Depends(get_db), openai_client: openai.AsyncOpenAI = Depends(get_openai_client)):
    logger = logging.getLogger("handle_callback")
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    body = body.decode()

    try:
        parser = WebhookParser(app_settings.line_channel_secret)
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if isinstance(event, PostbackEvent):
            data = parse_qs(event.postback.data)
            data = {k: v[0] for k, v in data.items()}
            if data["action"] == "select_model":
                await handle_action_select_model(event, data, linebot_api, db, openai_client)
            elif data["action"] == "xxx":
                pass
            else:
                await linebot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token = event.reply_token,
                        messages = [TextMessage(text="未知アクション")]
                    )
                )
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            profile = await linebot_api.get_profile(event.source.user_id)
            logger.info(f"{profile.display_name}（{profile.user_id}）からメッセージが届けました。")
            print(profile.display_name)
            msg_txt = event.message.text

            command_handle_rtn = await command.handle(msg_txt, linebot_api = linebot_api, db = db, event = event, openai_client = openai_client)
            if command_handle_rtn is None:
                await linebot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token = event.reply_token,
                        messages = [TextMessage(text="未知コマンド")]
                    )
                )
                continue
            if command_handle_rtn:
                continue
            await handle_message(event, linebot_api, db, openai_client)
            continue
    return 'OK'

@app.get("/health")
async def health():
    return 'OK'

@command.add("me")
async def command_new(content, linebot_api: AsyncMessagingApi = ..., db: Database = ..., event = ..., openai_client: openai.AsyncOpenAI = ...):
    profile = await linebot_api.get_profile(event.source.user_id)
    await linebot_api.reply_message(
        ReplyMessageRequest(
            reply_token = event.reply_token,
            messages = [TextMessage(text=f"名前：{profile.display_name}\nID：{profile.user_id}")]
        )
    )

@command.add("model")
async def command_new(content, linebot_api: AsyncMessagingApi = ..., db: Database = ..., event = ..., openai_client: openai.AsyncOpenAI = ...):
    user_id = event.source.user_id
    user = await db.fetch_user(user_id, next(iter(app_settings.assistants)), next(iter(app_settings.models)))

    columns = []
    for key, value in app_settings.models.items():
        column = CarouselColumn(
            text = f"{'**' if user['model'] == key else ''}モデル：{value['model']}\n賢い：{value['intelligence']}\nスピード：{value['speed']}\n値段：\n  入力：{value['pricing']['input']}\n  出力：{value['pricing']['output']}",
            actions = [PostbackAction(label="選択", data=urlencode({
                "action": "select_model",
                "model": key
            }))]
        )
        columns.append(column)

    await linebot_api.reply_message(
        ReplyMessageRequest(
            reply_token = event.reply_token,
            messages = [TemplateMessage(
                alt_text = "モデルを選択してください。",
                template = CarouselTemplate(
                    columns = columns
                )
            )]
        )
    )
    


@command.add("assistant")
async def command_new(content, linebot_api: AsyncMessagingApi = ..., db: Database = ..., event = ..., openai_client: openai.AsyncOpenAI = ...):
    pass

@command.add("new")
async def command_new(content, linebot_api: AsyncMessagingApi = ..., db: Database = ..., event = ..., openai_client: openai.AsyncOpenAI = ...):
    user_id = event.source.user_id
    user = await db.fetch_user(user_id, next(iter(app_settings.assistants)), next(iter(app_settings.models)))
    await db.update_user(user["_id"], {"$set": {"conversation_history": []}})
    await linebot_api.reply_message(
        ReplyMessageRequest(
            reply_token = event.reply_token,
            messages = [TextMessage(text="セッションがクリアしました。")]
        )
    )

@command.add("help")
async def command_help(content, linebot_api: AsyncMessagingApi = ..., db: Database = ..., event = ..., openai_client: openai.AsyncOpenAI = ...):
    await linebot_api.reply_message(
        ReplyMessageRequest(
            reply_token = event.reply_token,
            messages = [TextMessage(text=textwrap.dedent("""
                                                         /new：セッションクリア
                                                         /model：openaiのモデルを選択
                                                         /assistant：openaiのアシスタントを選択
                                                         /me：自分の情報を表示
                                                         """).strip())]
        )
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)
