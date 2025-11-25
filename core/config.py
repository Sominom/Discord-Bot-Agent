import os
import json
from core.logger import logger

class Settings:
    def __init__(self):
        self._config = {}
        # 1. config.json 로드
        self._load_json_config()
        
        # 2. 설정값 로드
        self.DISCORD_BOT_KEY = self._get_config("DISCORD_BOT_KEY")
        
        # 소유자 ID 처리 (리스트 또는 문자열)
        self.DISCORD_OWNER_IDS = self._get_config("DISCORD_OWNER_IDS", [])
        if isinstance(self.DISCORD_OWNER_IDS, str):
            self.DISCORD_OWNER_IDS = [x.strip() for x in self.DISCORD_OWNER_IDS.split(",") if x.strip()]
        
        self.OPENAI_API_KEY = self._get_config("OPENAI_API_KEY")
        self.OPENAI_MODEL = self._get_config("OPENAI_MODEL", "gpt-4.1-mini")
        
        self.GOOGLE_API_KEY = self._get_config("GOOGLE_API_KEY")
        self.VERTEX_API_KEY = self._get_config("VERTEX_API_KEY")
        self.CUSTOM_SEARCH_ENGINE_ID = self._get_config("CUSTOM_SEARCH_ENGINE_ID")
        
        self.HISTORY_NUM = self._get_int_config("HISTORY_NUM", 5)
        self.MAX_HISTORY_COUNT = self._get_int_config("MAX_HISTORY_COUNT", 5)
        self.MAX_RESPONSE_TOKENS = self._get_int_config("MAX_RESPONSE_TOKENS", 2000)
        
        self.BOT_NAME = self._get_config("BOT_NAME", "괴상한 봇")
        self.BOT_IDENTITY = self._get_config("BOT_IDENTITY", "당신은 괴상한 개발자 모임인 괴상한 괴발자 디스코드 채널의 봇입니다. 당신은 괴상한 개발자 모임의 일원이며, 디스코드 서버를 관리하고, 개발자들을 돕습니다.")
        self.BOT_START_MESSAGE = self._get_config("BOT_START_MESSAGE", "앗! 안녕하세요! 저는 괴상한 봇입니다! 무엇이든 물어봐주세요! U3U~ <3")
        
        logger.log("설정 로드 완료", logger.INFO)

    def _load_json_config(self):
        """config.json 파일 로드"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                logger.log(f"config.json 파일을 찾을 수 없습니다: {config_path}", logger.WARNING)
        except Exception as e:
            logger.log(f"config.json 로드 중 오류: {e}", logger.ERROR)

    def _get_config(self, key, default=None):
        return self._config.get(key, default)

    def _get_int_config(self, key, default=None):
        """설정값을 정수로 가져옵니다."""
        val = self._config.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except ValueError:
            logger.log(f"설정 오류: {key}의 값이 정수가 아닙니다 ({val}). 기본값 {default}를 사용합니다.", logger.WARNING)
            return default

# 전역 설정 인스턴스
env = Settings()
