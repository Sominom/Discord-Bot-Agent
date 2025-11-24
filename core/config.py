import os
import json
from dotenv import load_dotenv
from core.logger import logger

class Settings:
    def __init__(self):
        # 1. config.json이 있으면 먼저 로드하여 환경 변수에 설정 (호환성 유지)
        self._load_json_config()
        
        # 2. .env 파일 로드 (이미 설정된 환경 변수는 덮어쓰지 않음)
        load_dotenv()
        
        # 3. 설정값 로드
        self.DISCORD_BOT_KEY = os.getenv("DISCORD_BOT_KEY")
        
        # 숫자형 변환 처리
        self.DISCORD_OWNER_ID = os.getenv("DISCORD_OWNER_ID")
        
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
        
        self.HISTORY_NUM = self._get_int_env("HISTORY_NUM", 5)
        self.MAX_HISTORY_COUNT = self._get_int_env("MAX_HISTORY_COUNT", 5)
        
        logger.log("설정 로드 완료", logger.INFO)

    def _load_json_config(self):
        """config.json 파일이 있다면 환경 변수로 로드합니다."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        # 값이 존재하고 환경변수에 아직 없다면 설정
                        if v is not None and k not in os.environ:
                            os.environ[k] = str(v)
                # logger.log("config.json 설정을 환경 변수에 반영했습니다.", logger.DEBUG)
        except Exception as e:
            logger.log(f"config.json 로드 중 오류 (무시됨): {e}", logger.WARNING)

    def _get_int_env(self, key, default=None):
        """환경 변수를 정수로 가져옵니다."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.log(f"설정 오류: {key}의 값이 정수가 아닙니다 ({value}). 기본값 {default}를 사용합니다.", logger.WARNING)
            return default

# 전역 설정 인스턴스
env = Settings()
