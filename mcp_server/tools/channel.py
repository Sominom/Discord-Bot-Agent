from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp.types import TextContent
import discord

# 스키마 정의를 상수로 분리하여 가독성 향상
CREATE_TEXT_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "name": {"type": "string", "description": "채널 이름"},
        "category_id": {"type": "string", "description": "카테고리 ID (선택사항)"},
        "topic": {"type": "string", "description": "채널 주제 (선택사항)"}
    },
    "required": ["server_id", "name"]
}

@tool_registry.register("create_text_channel", "새 텍스트 채널 생성", CREATE_TEXT_CHANNEL_SCHEMA)
async def create_text_channel(arguments: dict):
    server_id = int(arguments["server_id"])
    guild = await global_context.fetch_guild(server_id)
    
    category = None
    if "category_id" in arguments:
        try:
            # 캐시된 길드 정보 사용 시도 (동기 함수)
            cache_guild = global_context.get_guild_from_id(server_id)
            if cache_guild:
                category = cache_guild.get_channel(int(arguments["category_id"]))
        except Exception:
            pass # 카테고리 찾기 실패 시 무시하고 최상위에 생성

    channel = await guild.create_text_channel(
        name=arguments["name"],
        category=category,
        topic=arguments.get("topic"),
        reason="MCP를 통해 생성된 채널"
    )
    
    return [TextContent(
        type="text",
        text=f"텍스트 채널 #{channel.name} (ID: {channel.id}) 생성 완료"
    )]

CREATE_VOICE_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "name": {"type": "string", "description": "채널 이름"},
        "category_id": {"type": "string", "description": "채널을 배치할 카테고리 ID (선택사항)"},
        "user_limit": {"type": "integer", "description": "음성 채널 최대 사용자 수 (선택사항)"},
        "bitrate": {"type": "integer", "description": "음성 채널 비트레이트 (선택사항)"}
    },
    "required": ["server_id", "name"]
}

@tool_registry.register("create_voice_channel", "새 음성 채널 생성", CREATE_VOICE_CHANNEL_SCHEMA)
async def create_voice_channel(arguments: dict):
    server_id = int(arguments["server_id"])
    guild = await global_context.fetch_guild(server_id)
    category = None
    
    if "category_id" in arguments:
        cache_guild = global_context.get_guild_from_id(server_id)
        if not cache_guild:
            return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다. 봇이 서버에 제대로 초대되었는지 확인하세요.")]
        
        category = cache_guild.get_channel(int(arguments["category_id"]))
        if not category or category.type != discord.ChannelType.category:
            return [TextContent(type="text", text="카테고리를 찾을 수 없거나 올바른 카테고리가 아닙니다.")]
    
    channel = await guild.create_voice_channel(
        name=arguments["name"],
        category=category,
        user_limit=arguments.get("user_limit"),
        bitrate=arguments.get("bitrate"),
        reason="MCP를 통해 생성된 음성 채널"
    )
    
    return [TextContent(
        type="text",
        text=f"음성 채널 🔊 {channel.name} (ID: {channel.id}) 생성 완료"
    )]

CREATE_CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "name": {"type": "string", "description": "카테고리 이름"},
        "position": {"type": "integer", "description": "카테고리 위치 (선택사항)"}
    },
    "required": ["server_id", "name"]
}

@tool_registry.register("create_category", "새 카테고리 생성", CREATE_CATEGORY_SCHEMA)
async def create_category(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    category = await guild.create_category(
        name=arguments["name"],
        position=arguments.get("position"),
        reason="MCP를 통해 생성된 카테고리"
    )
    
    return [TextContent(
        type="text",
        text=f"카테고리 📂 {category.name} (ID: {category.id}) 생성 완료"
    )]

DELETE_CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "category_id": {"type": "string", "description": "삭제할 카테고리 ID"}
    },
    "required": ["server_id", "category_id"]
}

@tool_registry.register("delete_category", "카테고리 삭제 (포함된 채널은 삭제되지 않음)", DELETE_CATEGORY_SCHEMA)
async def delete_category(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다. 봇이 서버에 제대로 초대되었는지 확인하세요.")]
    
    category = cache_guild.get_channel(int(arguments["category_id"]))
    
    if not category or category.type != discord.ChannelType.category:
        return [TextContent(
            type="text",
            text=f"카테고리를 찾을 수 없거나 올바른 카테고리가 아닙니다."
        )]
        
    await category.delete(reason="MCP를 통해 삭제된 카테고리")
    return [TextContent(
        type="text",
        text=f"카테고리 '{category.name}' 삭제 완료"
    )]

MOVE_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"},
        "channel_id": {"type": "string", "description": "이동할 채널 ID"},
        "category_id": {"type": "string", "description": "대상 카테고리 ID (비우면 카테고리 없음)"}
    },
    "required": ["server_id", "channel_id"]
}

@tool_registry.register("move_channel", "채널을 다른 카테고리로 이동", MOVE_CHANNEL_SCHEMA)
async def move_channel(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다. 봇이 서버에 제대로 초대되었는지 확인하세요.")]
    
    channel = cache_guild.get_channel(int(arguments["channel_id"]))
    
    if not channel:
        return [TextContent(
            type="text",
            text=f"채널을 찾을 수 없습니다."
        )]
        
    category = None
    if "category_id" in arguments and arguments["category_id"]:
        category = cache_guild.get_channel(int(arguments["category_id"]))
        if not category or category.type != discord.ChannelType.category:
            return [TextContent(
                type="text",
                text=f"대상 카테고리를 찾을 수 없거나 올바른 카테고리가 아닙니다."
            )]
    
    # 채널 이동
    await channel.edit(category=category, reason="MCP를 통해 이동된 채널")
    
    if category:
        return [TextContent(
            type="text",
            text=f"채널 '{channel.name}'을(를) 카테고리 '{category.name}'(으)로 이동 완료"
        )]
    else:
        return [TextContent(
            type="text",
            text=f"채널 '{channel.name}'을(를) 카테고리 없음으로 이동 완료"
        )]

RENAME_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "변경할 채널 ID"},
        "new_name": {"type": "string", "description": "새 채널 이름"}
    },
    "required": ["channel_id", "new_name"]
}

@tool_registry.register("rename_channel", "채널 이름 변경", RENAME_CHANNEL_SCHEMA)
async def rename_channel(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    old_name = channel.name
    
    await channel.edit(name=arguments["new_name"], reason="MCP를 통해 이름 변경")
    
    return [TextContent(
        type="text",
        text=f"채널 이름 변경 완료: '{old_name}' → '{arguments['new_name']}'"
    )]

DELETE_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "삭제할 채널 ID"},
        "reason": {"type": "string", "description": "삭제 이유"}
    },
    "required": ["channel_id"]
}

@tool_registry.register("delete_channel", "채널 삭제", DELETE_CHANNEL_SCHEMA)
async def delete_channel(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    await channel.delete(reason=arguments.get("reason", "MCP를 통해 삭제된 채널"))
    return [TextContent(type="text", text="채널 삭제 완료")]
