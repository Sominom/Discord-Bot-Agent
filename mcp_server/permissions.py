import discord
from core.config import env
from core.logger import logger
from mcp_server.context import global_context
from mcp.types import TextContent

def check_admin_permission():
    """
    현재 컨텍스트의 사용자가 관리자 권한을 가지고 있는지 확인합니다.
    관리자 권한:
    1. 봇 소유자 (env.DISCORD_OWNER_IDS)
    2. 서버 관리자 권한 보유자 (Administrator permission)
    3. 서버 소유자
    """
    message = global_context.get_current_message()
    if not message:
        logger.log("권한 확인 실패: 메시지 컨텍스트 없음", logger.WARNING)
        return False

    user = message.author
    
    # 1. 봇 소유자 확인
    if str(user.id) in env.DISCORD_OWNER_IDS:
        return True
        
    # DM인 경우 소유자만 가능
    if not message.guild:
        return False

    # 2. 서버 소유자 확인
    if message.guild.owner_id == user.id:
        return True

    # 3. 관리자 권한 확인
    # message.author는 Member 객체여야 guild_permissions 속성을 가짐
    if isinstance(user, discord.Member):
        if user.guild_permissions.administrator:
            return True
            
    return False

def admin_required(func):
    """
    관리자 권한이 필요한 툴에 적용하는 데코레이터입니다.
    권한이 없으면 실행을 막고 에러 메시지를 반환합니다.
    """
    async def wrapper(arguments: dict):
        if not check_admin_permission():
            return [TextContent(
                type="text",
                text="❌ 이 기능을 사용할 권한이 없습니다. (관리자 전용)"
            )]
        return await func(arguments)
    return wrapper

