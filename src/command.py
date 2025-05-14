# -*- coding: utf-8 -*-

import re

class Command():
    def __init__(self) -> None:
        self.__handler = {}
        self.__command_re = re.compile("^/(\\S+)(\\s+(.+))?$")

    async def handle(self, message_text: str, **args) -> bool:
        message_text = message_text.strip()
        matcher = self.__command_re.match(message_text)
        if matcher is None:
            return False
        command = matcher.groups()[0]
        content = matcher.groups()[2]
        if command not in self.__handler:
            return None
        await self.__handler[command](content, **args)
        return True

    def add(self, command: str = None):
        def decorator(func):
            nonlocal command
            self.__handler[command] = func
            return func
        return decorator