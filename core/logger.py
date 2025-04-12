"""
봇 로깅 시스템을 제공하는 모듈
콘솔 출력 및 파일 로깅 기능을 지원합니다.
"""

import logging
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style

class Logger:
    """
    봇 로깅 관리 클래스
    콘솔 및 파일 로그를 관리합니다.
    """
    
    def __init__(self, log_file="bot.log", max_bytes=5*1024*1024, backup_count=5):
        """
        로거 초기화
        
        Args:
            log_file: 로그 파일 경로
            max_bytes: 로그 파일 최대 크기
            backup_count: 백업 파일 개수
        """
        self.logger = logging.getLogger('bot_logger')
        self.logger.setLevel(logging.DEBUG)
        
        # 로거 핸들러가 없는 경우에만 추가
        if not self.logger.handlers:
            # 로그 포맷 설정
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # 콘솔 핸들러 추가
            console_handler = LogHandler(self)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # 파일 핸들러 추가
            try:
                file_handler = RotatingFileHandler(
                    log_file, 
                    maxBytes=max_bytes, 
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"로그 파일을 생성할 수 없습니다: {str(e)}")
        
        # 로그 레벨 상수
        self.DEBUG = logging.DEBUG
        self.INFO = logging.INFO
        self.WARNING = logging.WARNING
        self.ERROR = logging.ERROR
        self.CRITICAL = logging.CRITICAL
    
    def log(self, message, level=logging.INFO):
        """
        로그 메시지 기록
        
        Args:
            message: 로그 메시지
            level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if level == logging.DEBUG:
            self.logger.debug(message)
        elif level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        elif level == logging.CRITICAL:
            self.logger.critical(message)
    
    def process_log(self, record):
        """
        로그 메시지 처리 및 콘솔 출력
        
        Args:
            record: 로그 레코드 객체
        """
        # 로그 레벨별 색상 설정
        COLORS = {
            logging.DEBUG: Fore.CYAN,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA
        }
        
        # 로그 메시지 포맷 및 출력
        log_color = COLORS.get(record.levelno, Fore.WHITE)
        if self.logger.handlers and self.logger.handlers[0].formatter:
            formatted_message = self.logger.handlers[0].formatter.format(record)
        else:
            formatted_message = record.getMessage()
        print(f"{log_color}{formatted_message}{Style.RESET_ALL}")


class LogHandler(logging.Handler):
    """
    커스텀 로그 핸들러
    콘솔 출력을 담당합니다.
    """
    
    def __init__(self, logger):
        """
        핸들러 초기화
        
        Args:
            logger: 연결할 로거 객체
        """
        super().__init__()
        self.logger = logger
    
    def emit(self, record):
        """
        로그 레코드 처리
        
        Args:
            record: 로그 레코드 객체
        """
        self.logger.process_log(record)

# 싱글톤 인스턴스 생성
logger = Logger()

# 예제
if __name__ == "__main__":
    logger.log("This is a debug message", logger.DEBUG)
    logger.log("This is an info message", logger.INFO)
    logger.log("This is a warning message", logger.WARNING)
    logger.log("This is an error message", logger.ERROR)
    logger.log("This is a critical message", logger.CRITICAL) 