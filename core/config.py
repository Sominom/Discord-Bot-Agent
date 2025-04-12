from core.logger import Logger
import json
import os
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

logger = Logger()

class Config:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        self.load_config()
        
    def load_config(self):
        """설정 파일에서 환경 변수를 로드합니다."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # 모든 설정을 인스턴스 속성으로 추가
            for key, value in config_data.items():
                setattr(self, key, value)
                
            logger.log(f"설정 파일을 성공적으로 로드했습니다: {self.config_path}", logger.INFO)
        except Exception as e:
            logger.log(f"설정 파일 로드 중 오류 발생: {str(e)}", logger.ERROR)
            raise
        
env = Config()