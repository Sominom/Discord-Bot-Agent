import logging
from colorama import Fore, Style

class BotLogger:
    def __init__(self):
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            handler = LogHandler(self)
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
        
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
        COLORS = {
            logging.DEBUG: Fore.CYAN,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA
        }
        
        log_color = COLORS.get(record.levelno, Fore.WHITE)
        if self.logger.handlers and self.logger.handlers[0].formatter:
            formatted_message = self.logger.handlers[0].formatter.format(record)
        else:
            formatted_message = record.getMessage()
        print(f"{log_color}{formatted_message}{Style.RESET_ALL}")

class LogHandler(logging.Handler):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
    
    def emit(self, record):
        self.logger.process_log(record)

# 예제
if __name__ == "__main__":
    logger = BotLogger()
    logger.log("This is a debug message", logger.DEBUG)
    logger.log("This is an info message", logger.INFO)
    logger.log("This is a warning message", logger.WARNING)
    logger.log("This is an error message", logger.ERROR)
    logger.log("This is a critical message", logger.CRITICAL)
