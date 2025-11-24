from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp.types import TextContent
import discord

GET_SERVER_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버(길드) ID"}
    },
    "required": ["server_id"]
}

@tool_registry.register("get_server_info", "디스코드 서버 정보 조회", GET_SERVER_INFO_SCHEMA)
async def get_server_info(arguments: dict):
    guild = await global_context.fetch_guild(int(arguments["server_id"]))
    info = {
        "name": guild.name,
        "id": str(guild.id),
        "owner_id": str(guild.owner_id),
        "member_count": guild.member_count,
        "created_at": guild.created_at.isoformat(),
        "description": guild.description,
        "premium_tier": guild.premium_tier,
        "explicit_content_filter": str(guild.explicit_content_filter)
    }
    return [TextContent(
        type="text",
        text=f"서버 정보:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
    )]

LIST_CATEGORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "디스코드 서버 ID"}
    },
    "required": ["server_id"]
}

@tool_registry.register("list_categories", "서버의 카테고리 목록 조회", LIST_CATEGORIES_SCHEMA)
async def list_categories(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다. 봇이 서버에 제대로 초대되었는지 확인하세요.")]
    
    categories = []
    for category in cache_guild.categories:
        channel_list = []
        for channel in category.channels:
            channel_type = "🔊" if channel.type == discord.ChannelType.voice else "#"
            channel_list.append(f"{channel_type} {channel.name} (ID: {channel.id})")
        
        categories.append({
            "id": str(category.id),
            "name": category.name,
            "position": category.position,
            "channels": channel_list
        })
    
    if not categories:
        return [TextContent(
            type="text",
            text=f"서버에 카테고리가 없습니다."
        )]
        
    result = "카테고리 목록:\n\n"
    for cat in categories:
        result += f"📂 {cat['name']} (ID: {cat['id']})\n"
        if cat['channels']:
            for channel in cat['channels']:
                result += f"  - {channel}\n"
        else:
            result += "  (채널 없음)\n"
        result += "\n"
    
    return [TextContent(type="text", text=result.strip())]

CREATE_INVITE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "채널 ID"},
        "max_age": {"type": "integer", "description": "초대 링크 유효 시간(초), 0은 무제한"},
        "max_uses": {"type": "integer", "description": "최대 사용 횟수, 0은 무제한"},
        "temporary": {"type": "boolean", "description": "임시 멤버십 여부"}
    },
    "required": ["channel_id"]
}

@tool_registry.register("create_invite", "서버 초대 링크 생성", CREATE_INVITE_SCHEMA)
async def create_invite(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    
    max_age = arguments.get("max_age", 86400)  # 기본 24시간
    max_uses = arguments.get("max_uses", 0)  # 기본 무제한
    temporary = arguments.get("temporary", False)
    
    invite = await channel.create_invite(
        max_age=max_age,
        max_uses=max_uses,
        temporary=temporary,
        reason="MCP를 통해 생성된 초대 링크"
    )
    
    expiry_info = "무제한" if max_age == 0 else f"{max_age}초"
    usage_info = "무제한" if max_uses == 0 else f"{max_uses}회"
    
    return [TextContent(
        type="text",
        text=f"초대 링크 생성 완료: {invite.url}\n유효 기간: {expiry_info}, 최대 사용: {usage_info}, 임시 멤버십: {temporary}"
    )]

SET_SLOWMODE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "채널 ID"},
        "seconds": {"type": "integer", "description": "메시지 사이 간격(초)", "minimum": 0, "maximum": 21600}
    },
    "required": ["channel_id", "seconds"]
}

@tool_registry.register("set_slowmode", "채널 슬로우 모드 설정", SET_SLOWMODE_SCHEMA)
async def set_slowmode(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    seconds = min(max(int(arguments["seconds"]), 0), 21600)
    
    await channel.edit(slowmode_delay=seconds, reason="MCP를 통해 슬로우 모드 설정")
    
    if seconds == 0:
        return [TextContent(type="text", text=f"채널 '{channel.name}'의 슬로우 모드가 비활성화되었습니다.")]
    else:
        return [TextContent(type="text", text=f"채널 '{channel.name}'의 슬로우 모드가 {seconds}초로 설정되었습니다.")]

GET_SERVER_ID_FROM_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {"message_id": {"type": "string", "description": "메시지 ID (선택 사항)"}},
    "required": []
}

@tool_registry.register("get_server_id_from_message", "메시지에서 서버 ID를 자동으로 추출합니다.", GET_SERVER_ID_FROM_MESSAGE_SCHEMA)
async def get_server_id_from_message(arguments: dict):
    message_id = arguments.get("message_id")
    
    if not message_id:
        current_msg = global_context.get_current_message()
        if current_msg and current_msg.guild:
            return [TextContent(
                type="text",
                text=f"서버 ID: {current_msg.guild.id}, 서버 이름: {current_msg.guild.name}, 채널: {current_msg.channel.name}"
            )]
        return [TextContent(type="text", text="현재 메시지에서 서버 ID를 추출할 수 없습니다.")]
    
    # 캐시에서 메시지 찾기 (client 필요)
    client = global_context.get_client()
    for message_obj in client.cached_messages:
        if message_obj.id == int(message_id):
            return [TextContent(
                type="text",
                text=f"서버 ID: {message_obj.guild.id}, 서버 이름: {message_obj.guild.name}, 채널: {message_obj.channel.name}"
            )]
            
    # 못 찾으면 전체 검색 (비효율적이지만 기능 유지)
    for guild in client.guilds:
        for channel in guild.text_channels:
            try:
                message = await channel.fetch_message(int(message_id))
                return [TextContent(
                    type="text",
                    text=f"서버 ID: {guild.id}, 서버 이름: {guild.name}, 채널: {channel.name}"
                )]
            except:
                continue
                
    return [TextContent(type="text", text=f"메시지 ID {message_id}를 찾을 수 없습니다.")]

SEARCH_CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "검색할 디스코드 서버 ID"},
        "channel_name": {"type": "string", "description": "검색할 채널 이름 (일부 또는 전체)"}
    },
    "required": ["server_id", "channel_name"]
}

@tool_registry.register("search_channel", "서버 내에서 채널 이름으로 채널을 검색합니다.", SEARCH_CHANNEL_SCHEMA)
async def search_channel(arguments: dict):
    cache_guild = global_context.get_guild_from_id(int(arguments["server_id"]))
    if not cache_guild:
        return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다.")]
        
    query = arguments["channel_name"].lower().strip()
    found_channels = []
    
    for channel in cache_guild.channels:
        if query in channel.name.strip().lower():
            channel_type_emoji = "#️⃣"
            if isinstance(channel, discord.VoiceChannel):
                channel_type_emoji = "🔊"
            elif isinstance(channel, discord.CategoryChannel):
                channel_type_emoji = "📂"
                
            found_channels.append({
                "id": str(channel.id),
                "name": channel.name,
                "type": channel_type_emoji
            })
            
    if not found_channels:
        return [TextContent(type="text", text=f"'{query}' 이름과 유사한 채널을 찾을 수 없습니다.")]
        
    result_text = f"'{query}' 이름으로 검색된 채널 목록:\n" + \
                  "\n".join([f"- {c['type']} {c['name']} (ID: {c['id']})" for c in found_channels])
    return [TextContent(type="text", text=result_text)]

GET_CHANNEL_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "정보를 조회할 채널 ID"}
    },
    "required": ["channel_id"]
}

@tool_registry.register("get_channel_info", "채널 ID로 채널의 상세 정보를 조회합니다.", GET_CHANNEL_INFO_SCHEMA)
async def get_channel_info(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    info = {
        "id": str(channel.id),
        "name": channel.name,
        "type": str(channel.type),
        "created_at": channel.created_at.isoformat(),
        "position": channel.position,
    }
    if isinstance(channel, discord.TextChannel):
        info["topic"] = channel.topic
        info["slowmode_delay"] = channel.slowmode_delay
        info["nsfw"] = channel.is_nsfw()
    elif isinstance(channel, discord.VoiceChannel):
        info["bitrate"] = channel.bitrate
        info["user_limit"] = channel.user_limit
        
    if hasattr(channel, 'category') and channel.category:
        info["category_id"] = str(channel.category.id)
        info["category_name"] = channel.category.name

    result_text = f"채널 정보 ({info['name']}):\n" + \
                  "\n".join([f"- {k}: {v}" for k, v in info.items()])
    return [TextContent(type="text", text=result_text)]

SET_CHANNEL_TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "주제를 설정할 텍스트 채널 ID"},
        "topic": {"type": "string", "description": "설정할 새로운 주제 내용"}
    },
    "required": ["channel_id", "topic"]
}

@tool_registry.register("set_channel_topic", "텍스트 채널의 주제(토픽)를 설정합니다.", SET_CHANNEL_TOPIC_SCHEMA)
async def set_channel_topic(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    if not isinstance(channel, discord.TextChannel):
         return [TextContent(type="text", text="텍스트 채널만 주제를 설정할 수 있습니다.")]
    await channel.edit(topic=arguments["topic"], reason="MCP를 통해 주제 설정")
    return [TextContent(type="text", text=f"채널 #{channel.name}의 주제가 성공적으로 변경되었습니다.")]

