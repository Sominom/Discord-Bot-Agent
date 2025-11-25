from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp_server.permissions import admin_required
from mcp.types import TextContent
import discord

ADD_ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "user_id": {"type": "string", "description": "역할을 추가할 사용자 ID (이름이나 ID 중 하나 필수)"},
        "user_name": {"type": "string", "description": "사용자 이름 또는 닉네임 (ID 대신 사용 가능)"},
        "role_id": {"type": "string", "description": "추가할 역할 ID (이름이나 ID 중 하나 필수)"},
        "role_name": {"type": "string", "description": "역할 이름 (ID 대신 사용 가능)"}
    },
    "required": ["server_id"]
}

async def _find_member(guild, user_id=None, user_name=None):
    if user_id:
        try:
            return await guild.fetch_member(int(user_id))
        except:
            return None
            
    if user_name:
        # 캐시된 멤버 중에서 검색
        found = []
        for member in guild.members:
            if user_name.lower() in member.name.lower() or (member.nick and user_name.lower() in member.nick.lower()):
                found.append(member)
        
        if len(found) == 1:
            return found[0]
        elif len(found) > 1:
            # 여러 명이면 에러 메시지 대신 None과 후보 리스트 반환 (여기선 간단히 예외 처리)
            names = ", ".join([f"{m.name}({m.nick})" for m in found[:5]])
            raise ValueError(f"'{user_name}' 검색 결과가 너무 많습니다: {names}...")
            
    return None

def _find_role(guild, role_id=None, role_name=None):
    if role_id:
        return guild.get_role(int(role_id))
        
    if role_name:
        found = []
        for role in guild.roles:
            if role_name.lower() == role.name.lower(): # 역할은 정확히 일치하는 게 좋음
                found.append(role)
            elif role_name.lower() in role.name.lower():
                found.append(role)
                
        # 정확히 일치하는 게 있으면 우선 반환
        exact = [r for r in found if r.name.lower() == role_name.lower()]
        if len(exact) == 1:
            return exact[0]
            
        if len(found) == 1:
            return found[0]
        elif len(found) > 1:
            names = ", ".join([r.name for r in found[:5]])
            raise ValueError(f"'{role_name}' 역할 검색 결과가 너무 많습니다: {names}...")
            
    return None

@tool_registry.register("add_role", "사용자에게 역할 추가", ADD_ROLE_SCHEMA)
@admin_required
async def add_role(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다.")]
    
    try:
        member = await _find_member(cache_guild, arguments.get("user_id"), arguments.get("user_name"))
        if not member:
            return [TextContent(type="text", text="사용자를 찾을 수 없습니다. 정확한 ID나 이름을 입력해주세요.")]
            
        role = _find_role(cache_guild, arguments.get("role_id"), arguments.get("role_name"))
        if not role:
            return [TextContent(type="text", text="역할을 찾을 수 없습니다. 정확한 ID나 이름을 입력해주세요.")]
            
        await member.add_roles(role, reason="MCP를 통해 추가된 역할")
        return [TextContent(
            type="text",
            text=f"{member.display_name} 사용자에게 '{role.name}' 역할 추가 완료"
        )]
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
         return [TextContent(type="text", text=f"오류 발생: {str(e)}")]

REMOVE_ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "user_id": {"type": "string", "description": "사용자 ID (선택)"},
        "user_name": {"type": "string", "description": "사용자 이름 (선택)"},
        "role_id": {"type": "string", "description": "역할 ID (선택)"},
        "role_name": {"type": "string", "description": "역할 이름 (선택)"}
    },
    "required": ["server_id"]
}

@tool_registry.register("remove_role", "사용자에게서 역할 제거", REMOVE_ROLE_SCHEMA)
@admin_required
async def remove_role(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다.")]
        
    try:
        member = await _find_member(cache_guild, arguments.get("user_id"), arguments.get("user_name"))
        if not member:
            return [TextContent(type="text", text="사용자를 찾을 수 없습니다.")]
            
        role = _find_role(cache_guild, arguments.get("role_id"), arguments.get("role_name"))
        if not role:
            return [TextContent(type="text", text="역할을 찾을 수 없습니다.")]
            
        await member.remove_roles(role, reason="MCP를 통해 제거된 역할")
        return [TextContent(
            type="text",
            text=f"{member.display_name} 사용자에게서 '{role.name}' 역할 제거 완료"
        )]
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
         return [TextContent(type="text", text=f"오류 발생: {str(e)}")]

CREATE_ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "역할을 생성할 서버 ID"},
        "name": {"type": "string", "description": "새 역할의 이름"},
        "permissions": {"type": "string", "description": "역할에 부여할 권한 값 (discord.Permissions 정수 값, 선택사항)"},
        "colour": {"type": "string", "description": "역할 색상 (헥스 코드, 예: '#FF0000', 선택사항)"},
        "hoist": {"type": "boolean", "description": "온라인 멤버 목록에 별도 표시 여부 (선택사항)"},
        "mentionable": {"type": "boolean", "description": "역할을 멘션할 수 있는지 여부 (선택사항)"}
    },
    "required": ["server_id", "name"]
}

@tool_registry.register("create_role", "서버에 새로운 역할을 생성합니다.", CREATE_ROLE_SCHEMA)
@admin_required
async def create_role(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    perms_int = int(arguments.get("permissions", 0))
    permissions = discord.Permissions(perms_int)
    colour_hex = arguments.get("colour", "#000000")
    colour = discord.Colour.from_str(colour_hex)

    role = await guild.create_role(
        name=arguments["name"],
        permissions=permissions,
        colour=colour,
        hoist=arguments.get("hoist", False),
        mentionable=arguments.get("mentionable", False),
        reason="MCP를 통해 역할 생성"
    )
    return [TextContent(type="text", text=f"역할 '{role.name}' (ID: {role.id})이(가) 성공적으로 생성되었습니다.")]

DELETE_ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "역할을 삭제할 서버 ID"},
        "role_id": {"type": "string", "description": "삭제할 역할 ID"},
        "reason": {"type": "string", "description": "삭제 이유 (선택사항)"}
    },
    "required": ["server_id", "role_id"]
}

@tool_registry.register("delete_role", "서버에서 역할을 삭제합니다.", DELETE_ROLE_SCHEMA)
@admin_required
async def delete_role(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다. 봇이 서버에 제대로 초대되었는지 확인하세요.")]
        
    role = cache_guild.get_role(int(arguments["role_id"]))
    if not role:
        return [TextContent(type="text", text=f"역할 ID {arguments['role_id']}를 찾을 수 없습니다.")]
    role_name = role.name
    await role.delete(reason=arguments.get("reason", "MCP를 통해 역할 삭제"))
    return [TextContent(type="text", text=f"역할 '{role_name}'이(가) 성공적으로 삭제되었습니다.")]

