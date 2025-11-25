from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp_server.permissions import admin_required
from mcp.types import TextContent
import discord

LIST_MEMBERS_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "limit": {"type": "number", "description": "가져올 최대 멤버 수", "minimum": 1, "maximum": 1000}
    },
    "required": ["server_id"]
}

@tool_registry.register("list_members", "서버 멤버 목록 조회", LIST_MEMBERS_SCHEMA)
async def list_members(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    limit = min(int(arguments.get("limit", 100)), 1000)
    
    members = []
    async for member in guild.fetch_members(limit=limit):
        members.append({
            "id": str(member.id),
            "name": member.name,
            "nick": member.nick,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "roles": [str(role.id) for role in member.roles[1:]]  # @everyone 역할 제외
        })
    
    return [TextContent(
        type="text",
        text=f"서버 멤버 ({len(members)}명):\n" + 
                "\n".join(f"{m['name']} (ID: {m['id']}, 역할: {', '.join(m['roles'])})" for m in members)
    )]

KICK_MEMBER_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "멤버를 추방할 서버 ID"},
        "user_id": {"type": "string", "description": "추방할 사용자 ID"},
        "reason": {"type": "string", "description": "추방 이유 (선택사항)"}
    },
    "required": ["server_id", "user_id"]
}

@tool_registry.register("kick_member", "서버에서 멤버를 추방합니다.", KICK_MEMBER_SCHEMA)
@admin_required
async def kick_member(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    member = await guild.fetch_member(int(arguments["user_id"]))
    member_name = member.display_name
    await guild.kick(member, reason=arguments.get("reason", "MCP를 통해 추방됨"))
    return [TextContent(type="text", text=f"멤버 '{member_name}'(이)가 서버에서 추방되었습니다.")]

BAN_MEMBER_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "멤버를 차단할 서버 ID"},
        "user_id": {"type": "string", "description": "차단할 사용자 ID"},
        "reason": {"type": "string", "description": "차단 이유 (선택사항)"},
        "delete_message_days": {"type": "integer", "description": "차단 시 삭제할 메시지 기간(일) (0-7, 선택사항, 기본값 0)", "minimum": 0, "maximum": 7}
    },
    "required": ["server_id", "user_id"]
}

@tool_registry.register("ban_member", "서버에서 멤버를 차단합니다.", BAN_MEMBER_SCHEMA)
@admin_required
async def ban_member(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    # fetch_user 사용: 서버에 없어도 ID로 차단 가능
    user = await global_context.fetch_user(int(arguments["user_id"]))
    user_name = user.display_name
    delete_days = int(arguments.get("delete_message_days", 0))
    await guild.ban(
        user,
        reason=arguments.get("reason", "MCP를 통해 차단됨"),
        delete_message_days=delete_days
    )
    return [TextContent(type="text", text=f"사용자 '{user_name}'(이)가 서버에서 차단되었습니다. (메시지 {delete_days}일치 삭제)")]

DISCONNECT_MEMBER_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "user_id": {"type": "string", "description": "연결 끊을 사용자 ID"}
    },
    "required": ["server_id", "user_id"]
}

@tool_registry.register("disconnect_member", "음성 채널에서 멤버 연결 끊기", DISCONNECT_MEMBER_SCHEMA)
@admin_required
async def disconnect_member(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    member = await guild.fetch_member(int(arguments["user_id"]))
    
    if not member.voice:
        return [TextContent(
            type="text",
            text=f"사용자 '{member.name}'는 현재 음성 채널에 연결되어 있지 않습니다."
        )]
        
    await member.move_to(None, reason="MCP를 통해 연결 끊김")
    
    return [TextContent(
        type="text",
        text=f"사용자 '{member.name}'의 음성 채널 연결이 끊겼습니다."
    )]

CHANGE_NICKNAME_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "닉네임을 변경할 서버 ID"},
        "user_id": {"type": "string", "description": "닉네임을 변경할 사용자 ID"},
        "nickname": {"type": "string", "description": "새로운 닉네임 (비워두면 닉네임 제거)"}
    },
    "required": ["server_id", "user_id", "nickname"]
}

@tool_registry.register("change_nickname", "서버 내 사용자의 닉네임을 변경합니다.", CHANGE_NICKNAME_SCHEMA)
@admin_required
async def change_nickname(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    member = await guild.fetch_member(int(arguments["user_id"]))
    old_nick = member.display_name
    new_nick = arguments["nickname"] if arguments["nickname"] else None # 빈 문자열은 None으로 처리
    await member.edit(nick=new_nick, reason="MCP를 통해 닉네임 변경")
    if new_nick:
            return [TextContent(type="text", text=f"사용자 '{old_nick}'의 닉네임이 '{new_nick}'(으)로 변경되었습니다.")]
    else:
            return [TextContent(type="text", text=f"사용자 '{old_nick}'의 닉네임이 제거되었습니다.")]

GET_USER_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "string", "description": "디스코드 사용자 ID"}
    },
    "required": ["user_id"]
}

@tool_registry.register("get_user_info", "디스코드 사용자 정보 조회", GET_USER_INFO_SCHEMA)
async def get_user_info(arguments: dict):
    user = await global_context.fetch_user(int(arguments["user_id"]))
    user_info = {
        "id": str(user.id),
        "name": user.name,
        "discriminator": user.discriminator if hasattr(user, 'discriminator') else None,
        "bot": user.bot,
        "created_at": user.created_at.isoformat()
    }
    return [TextContent(
        type="text",
        text=f"사용자 정보:\n" + 
                f"이름: {user_info['name']}\n" +
                f"ID: {user_info['id']}\n" +
                f"봇 여부: {user_info['bot']}\n" +
                f"계정 생성일: {user_info['created_at']}"
    )]

