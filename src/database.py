# -*- coding: utf-8 -*-

import asyncio
import os
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

class Database():
    def __init__(self, mongo_url: str, database_name: str) -> None:
        self.__client = AsyncIOMotorClient(mongo_url)
        self.__db = self.__client[database_name]
        # self.__collection_assistant = self.__db["assistant"]
        self.__collection_user = self.__db["user"]

    # async def fetch_all_assistant(self):
    #     return self.__collection_assistant.find({})
    
    # async def fetch_assistant(self, key: str, model: str):
    #     return await self.__collection_assistant.find_one({"key": key, "model": model})
    
    # async def insert_assistant(self, key: str, id: str, model:str, props: dict):
    #     result = await self.__collection_assistant.insert_one({
    #         "key": key,
    #         "id": id,
    #         "model": model,
    #         "props": props
    #     })
    #     return result.inserted_id
    
    # async def delete_assistant(self, _id: str):
    #     await self.__collection_assistant.delete_one({'_id': ObjectId(_id)})
    
    async def fetch_user(self, id: str, default_assistant: str, default_model: str):
        user = await self.__collection_user.find_one({"id": id})
        if user:
            return user
        user = {
            "id": id,
            "assistant": default_assistant,
            "model": default_model,
            "conversation_history": []
        }
        user["_id"] = (await self.__collection_user.insert_one(user)).inserted_id
        return user

    async def update_user(self, _id: str, data: dict):
        await self.__collection_user.update_one({'_id': ObjectId(_id)}, data)
