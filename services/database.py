import os
import mysql.connector
from mysql.connector import Error
from core.logger import logger
from core.config import env

class Database:
    """데이터베이스 연결 및 작업을 위한 클래스"""
    
    def __init__(self):
        self.connection = None
        self.connect()
        self.setup_tables()
    
    def connect(self):
        """데이터베이스에 연결"""
        try:
            self.connection = mysql.connector.connect(
                host=env.MYSQL_HOST,
                user=env.MYSQL_USER,
                password=env.MYSQL_PASSWORD,
                database=env.MYSQL_DATABASE
            )
            if self.connection.is_connected():
                logger.log("MySQL 데이터베이스에 연결되었습니다.", logger.INFO)
        except Error as e:
            logger.log(f"MySQL 연결 오류: {e}", logger.ERROR)
            self.connection = None
    
    def setup_tables(self):
        """필요한 테이블 설정"""
        if not self.connection:
            logger.log("데이터베이스 연결이 없어 테이블 설정을 건너뜁니다.", logger.WARNING)
            return
            
        try:
            cursor = self.connection.cursor()
            
            # 채팅 채널 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_channels (
                    id BIGINT PRIMARY KEY,
                    guild_id BIGINT,
                    name VARCHAR(100),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 설정 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) UNIQUE,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            self.connection.commit()
            logger.log("데이터베이스 테이블이 설정되었습니다.", logger.INFO)
        except Error as e:
            logger.log(f"테이블 설정 오류: {e}", logger.ERROR)
    
    def get_chat_channels(self):
        """데이터베이스에서 채팅 채널 목록 가져오기"""
        if not self.connection:
            logger.log("데이터베이스 연결이 없어 빈 채널 목록을 반환합니다.", logger.WARNING)
            return []
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT id FROM chat_channels")
            channels = [channel_id[0] for channel_id in cursor.fetchall()]
            return channels
        except Error as e:
            logger.log(f"채널 목록 조회 오류: {e}", logger.ERROR)
            return []
    
    def add_chat_channel(self, channel_id, guild_id, name):
        """채팅 채널 추가"""
        if not self.connection:
            logger.log("데이터베이스 연결이 없어 채널을 추가할 수 없습니다.", logger.WARNING)
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO chat_channels (id, guild_id, name) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE guild_id=%s, name=%s",
                (channel_id, guild_id, name, guild_id, name)
            )
            self.connection.commit()
            logger.log(f"채널 추가됨: {channel_id} ({name})", logger.INFO)
            return True
        except Error as e:
            logger.log(f"채널 추가 오류: {e}", logger.ERROR)
            return False
    
    def delete_chat_channel(self, channel_id):
        """채팅 채널 삭제"""
        if not self.connection:
            logger.log("데이터베이스 연결이 없어 채널을 삭제할 수 없습니다.", logger.WARNING)
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM chat_channels WHERE id = %s", (channel_id,))
            self.connection.commit()
            logger.log(f"채널 삭제됨: {channel_id}", logger.INFO)
            return True
        except Error as e:
            logger.log(f"채널 삭제 오류: {e}", logger.ERROR)
            return False
    
    def get_setting(self, name, default=None):
        """설정값 가져오기"""
        if not self.connection:
            logger.log("데이터베이스 연결이 없어 기본값을 반환합니다.", logger.WARNING)
            return default
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE name = %s", (name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            return default
        except Error as e:
            logger.log(f"설정값 조회 오류: {e}", logger.ERROR)
            return default
    
    def set_setting(self, name, value):
        """설정값 저장하기"""
        if not self.connection:
            logger.log("데이터베이스 연결이 없어 설정을 저장할 수 없습니다.", logger.WARNING)
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO settings (name, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value=%s",
                (name, value, value)
            )
            self.connection.commit()
            logger.log(f"설정값 저장됨: {name}={value}", logger.INFO)
            return True
        except Error as e:
            logger.log(f"설정값 저장 오류: {e}", logger.ERROR)
            return False

# 데이터베이스 싱글톤 인스턴스
db = Database() 