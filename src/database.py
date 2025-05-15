# -*- coding: utf-8 -*-

import asyncio
import os
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

class Database():
    def __init__(self, mongo_url: str, database_name: str) -> None:
        self.__client = AsyncIOMotorClient(mongo_url)
        self.__db = self.__client[database_name]
        self.__collection_user = self.__db["user"]

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
