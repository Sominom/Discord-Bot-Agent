import discord
from typing import Optional, Tuple
from core.logger import logger

class MCPContext:
    """
    MCP 서비스 전반에서 공유되는 상태(봇 클라이언트, 현재 메시지 등)를 관리합니다.
    싱글톤 패턴과 유사하게 동작하지만, 명시적으로 주입하여 사용합니다.
    """
    def __init__(self):
        self._client: Optional[discord.Client] = None
        self._current_message: Optional[discord.Message] = None

    def set_client(self, client: discord.Client):
        self._client = client
        logger.log(f"MCP Context: 디스코드 클라이언트 설정됨 ({client.user})", logger.INFO)

    def get_client(self) -> discord.Client:
        if not self._client:
            raise RuntimeError("디스코드 클라이언트가 초기화되지 않았습니다.")
        return self._client

    def set_current_message(self, message: discord.Message):
        self._current_message = message
        # logger.log(f"MCP Context: 현재 메시지 컨텍스트 업데이트 ({message.id})", logger.DEBUG)

    def get_current_message(self) -> Optional[discord.Message]:
        return self._current_message

    def get_guild_from_id(self, guild_id: int) -> Optional[discord.Guild]:
        if not self._client:
            return None
        return self._client.get_guild(guild_id)

    async def fetch_guild(self, guild_id: int) -> discord.Guild:
        if not self._client:
            raise RuntimeError("Client not ready")
        return await self._client.fetch_guild(guild_id)

    async def fetch_channel(self, channel_id: int):
        if not self._client:
            raise RuntimeError("Client not ready")
        return await self._client.fetch_channel(channel_id)
    
    async def fetch_user(self, user_id: int):
        if not self._client:
            raise RuntimeError("Client not ready")
        return await self._client.fetch_user(user_id)

# 전역 컨텍스트 인스턴스 (필요시 모듈 레벨에서 접근)
global_context = MCPContext()

