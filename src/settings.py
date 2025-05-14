# -*- coding: utf-8 -*-

import yaml
from pydantic_settings import BaseSettings
from pydantic import model_validator
from pathlib import Path

class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    database: str = "line_chatgpt"
    line_channel_access_token: str
    line_channel_secret: str
    openai_api_key: str
    config_dir: str = "config"
    openai_base_url: str = "https://api.openai.com/v1"
    max_history: int = 10
    assistants: dict[str, dict] = {}
    models: dict[str, dict] = {}
    deny_list: list[str] = []
    allow_list: list[str] = []

    @staticmethod
    def __load_yaml_file(cls, file_path):
        with open(file_path, encoding='utf-8')as f:
            return yaml.safe_load(f)

    @model_validator(mode="after")
    def __load_yaml_file_value(cls, values):
        config_path = Path(values.config_dir)
        values.assistants = cls.__load_yaml_file(cls, config_path / "assistants.yml")
        values.models = cls.__load_yaml_file(cls, config_path / "models.yml")
        return values
