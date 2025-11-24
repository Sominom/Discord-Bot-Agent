from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp.types import TextContent
import discord
from services.database import add_chat_channel as db_add_chat_channel, delete_chat_channel as db_delete_chat_channel

ADD_CHAT_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "추가할 채널 ID (생략 시 현재 채널)"}
    },
    "required": []
}

@tool_registry.register("add_chat_channel", "봇이 대화에 참여할 채널로 추가 (이 채널의 메시지를 읽고 반응하게 됨)", ADD_CHAT_CHANNEL_SCHEMA)
async def add_chat_channel(arguments: dict):
    channel_id = arguments.get("channel_id")
    
    if channel_id:
        channel = await global_context.fetch_channel(int(channel_id))
    else:
        msg = global_context.get_current_message()
        if not msg:
             return [TextContent(type="text", text="현재 메시지 컨텍스트가 없어 채널 ID를 지정해야 합니다.")]
        channel = msg.channel
        
    guild_id = channel.guild.id if hasattr(channel, "guild") else 0
    
    success = db_add_chat_channel(channel.id, guild_id, channel.name)
    
    if success:
        return [TextContent(type="text", text=f"채널 '{channel.name}'(ID: {channel.id})이(가) 대화 채널로 추가되었습니다. 이제 여기서 봇과 자유롭게 대화할 수 있습니다.")]
    else:
        return [TextContent(type="text", text="채널 추가 중 오류가 발생했습니다.")]

REMOVE_CHAT_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "제거할 채널 ID (생략 시 현재 채널)"}
    },
    "required": []
}

@tool_registry.register("remove_chat_channel", "봇 대화 채널 목록에서 제거 (더 이상 이 채널에서 자동 반응하지 않음)", REMOVE_CHAT_CHANNEL_SCHEMA)
async def remove_chat_channel(arguments: dict):
    channel_id = arguments.get("channel_id")
    
    if channel_id:
        channel = await global_context.fetch_channel(int(channel_id))
        c_id = channel.id
        c_name = channel.name
    else:
        msg = global_context.get_current_message()
        if not msg:
             return [TextContent(type="text", text="현재 메시지 컨텍스트가 없어 채널 ID를 지정해야 합니다.")]
        c_id = msg.channel.id
        c_name = msg.channel.name if hasattr(msg.channel, "name") else "DM"
        
    success = db_delete_chat_channel(c_id)
    
    if success:
        return [TextContent(type="text", text=f"채널 '{c_name}'(ID: {c_id})이(가) 대화 채널에서 제거되었습니다.")]
    else:
        return [TextContent(type="text", text=f"채널 제거 실패: ID {c_id}를 목록에서 찾을 수 없습니다.")]

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
