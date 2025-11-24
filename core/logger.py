import logging
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style

class Logger:
    def __init__(self, log_file="bot.log", max_bytes=5*1024*1024, backup_count=5):
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
        
        # Stdio 통신을 위해 stdout 대신 stderr 사용
        import sys
        sys.stderr.write(f"{log_color}{formatted_message}{Style.RESET_ALL}\n")
        sys.stderr.flush()


import sys

class LogHandler(logging.Handler):
    
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
    
    def emit(self, record):
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