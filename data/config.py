import json
from data.bot_logger import BotLogger

Logger = BotLogger()

class Config:
    def __init__(self):
        self.config_file_path: str = "data/config.json"
        self.search_config_file_path: str = "data/search_config.json"

    def add_chat_channel(self, channel_id: str) -> None:
        config = self.config
        chat_channels = config.get("CHAT_CHANNELS", [])
        chat_channels.append(channel_id)
        config["CHAT_CHANNELS"] = chat_channels
        self.config = config

    def delete_chat_channel(self, channel_id: str) -> None:
        config = self.config
        chat_channels = config.get("CHAT_CHANNELS", [])
        if channel_id in chat_channels:
            chat_channels.remove(channel_id)
            config["CHAT_CHANNELS"] = chat_channels
            self.config = config

    @property
    def openai_model(self) -> list[str]:
        config = self.config
        return config.get("OPENAI_MODEL", [])
    
    @property
    def chat_channels(self) -> list[str]:
        config = self.config
        return config.get("CHAT_CHANNELS", [])
    
    @property
    def discord_bot_key(self) -> str:
        config = self.config
        return config.get("DISCORD_BOT_KEY", "")
    
    @property
    def openai_api_key(self) -> str:
        config = self.config
        return config.get("OPENAI_API_KEY", "")
    
    @property
    def google_api_key(self) -> str:
        config = self.config
        return config.get("GOOGLE_API_KEY", "")
    
    @property
    def custom_search_engine_id(self) -> str:
        config = self.config
        return config.get("CUSTOM_SEARCH_ENGINE_ID", "")

    @property
    def forbidden_search_keywords(self) -> list[str]:
        search_config = self.search_config
        return search_config.get("FORBIDDEN_SEARCH_KEYWORDS", [])
    
    @property
    def forbidden_domains(self) -> list[str]:
        search_config = self.search_config
        return search_config.get("FORBIDDEN_DOMAINS", [])
    
    @property
    def history_num(self) -> int:
        config = self.config
        return config.get("HISTORY_NUM", 3)
    

    @history_num.setter
    def history_num(self, value: int) -> None:
        config = self.config
        config["HISTORY_NUM"] = value
        self.config = config

    @property
    def config(self) -> dict:
        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except FileNotFoundError as e:
            Logger.log(f"설정 파일을 찾을 수 없습니다.\n{str(e)}", Logger.ERROR)
            return {}
        except json.JSONDecodeError as e:
            Logger.log(f"설정 파일을 파싱할 수 없습니다.\n{str(e)}", Logger.ERROR)
            return {}
        except Exception as e:
            Logger.log(f"설정 파일을 읽을 수 없습니다.\n{str(e)}", Logger.ERROR)
            return {}

    @config.setter
    def config(self, config: dict) -> None:
        try:
            with open(self.config_file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except FileNotFoundError as e:
            Logger.log(f"설정 파일을 찾을 수 없습니다.\n{str(e)}", Logger.ERROR)
        except json.JSONDecodeError as e:
            Logger.log(f"설정 파일을 파싱할 수 없습니다.\n{str(e)}", Logger.ERROR)
        except Exception as e:
            Logger.log(f"설정 파일을 쓸 수 없습니다.\n{str(e)}", Logger.ERROR)
            
    @property
    def search_config(self) -> dict:
        try:
            with open(self.search_config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except FileNotFoundError as e:
            Logger.log(f"검색 설정 파일을 찾을 수 없습니다.\n{str(e)}", Logger.ERROR)
            return {}
        except json.JSONDecodeError as e:
            Logger.log(f"검색 설정 파일을 파싱할 수 없습니다.\n{str(e)}", Logger.ERROR)
            return {}
        except Exception as e:
            Logger.log(f"검색 설정 파일을 읽을 수 없습니다.\n{str(e)}", Logger.ERROR)
            return {}
        