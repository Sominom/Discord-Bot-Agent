from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp.types import TextContent
import discord
from services.music_service import music_service

JOIN_VOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "입장할 음성 채널 ID (생략 시 사용자가 있는 채널)"}
    },
    "required": []
}

@tool_registry.register("join_voice_channel", "음성 채널에 입장합니다.", JOIN_VOICE_SCHEMA)
async def join_voice_channel(arguments: dict):
    channel_id = arguments.get("channel_id")
    
    if channel_id:
        channel = await global_context.fetch_channel(int(channel_id))
    else:
        # 사용자가 있는 채널 찾기
        guild = None
        msg = global_context.get_current_message()
        if msg:
            guild = msg.guild
            member = msg.author
            if isinstance(member, discord.Member) and member.voice:
                channel = member.voice.channel
            else:
                return [TextContent(type="text", text="음성 채널에 먼저 입장하거나 channel_id를 지정해주세요.")]
        else:
             return [TextContent(type="text", text="채널 정보를 찾을 수 없습니다.")]

    if not isinstance(channel, discord.VoiceChannel):
        return [TextContent(type="text", text="지정된 채널이 음성 채널이 아닙니다.")]

    await music_service.join_voice(channel)
    return [TextContent(type="text", text=f"음성 채널 '{channel.name}'에 입장했습니다.")]

LEAVE_VOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "description": "서버 ID (생략 시 현재 컨텍스트)"}
    },
    "required": []
}

@tool_registry.register("leave_voice_channel", "음성 채널에서 퇴장합니다.", LEAVE_VOICE_SCHEMA)
async def leave_voice_channel(arguments: dict):
    server_id = arguments.get("server_id")
    if server_id:
        guild = await global_context.fetch_guild(int(server_id))
    else:
        msg = global_context.get_current_message()
        if not msg:
             return [TextContent(type="text", text="현재 컨텍스트를 찾을 수 없습니다.")]
        guild = msg.guild

    success = await music_service.leave_voice(guild)
    if success:
        return [TextContent(type="text", text="음성 채널에서 퇴장했습니다.")]
    else:
        return [TextContent(type="text", text="현재 음성 채널에 있지 않습니다.")]

PLAY_MUSIC_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "노래 제목 또는 유튜브 URL"},
        "server_id": {"type": "string", "description": "서버 ID (생략 시 현재 컨텍스트)"}
    },
    "required": ["query"]
}

@tool_registry.register("play_music", "음악을 검색하여 재생 목록에 추가하고 재생합니다.", PLAY_MUSIC_SCHEMA)
async def play_music(arguments: dict):
    query = arguments["query"]
    server_id = arguments.get("server_id")
    
    if server_id:
        guild = await global_context.fetch_guild(int(server_id))
    else:
        msg = global_context.get_current_message()
        if not msg:
             return [TextContent(type="text", text="현재 컨텍스트를 찾을 수 없습니다.")]
        guild = msg.guild

    # 음성 채널 연결 확인
    if not guild.voice_client:
        # 사용자가 있는 곳으로 자동 입장 시도
        msg = global_context.get_current_message()
        if msg and isinstance(msg.author, discord.Member) and msg.author.voice:
             await music_service.join_voice(msg.author.voice.channel)
        else:
             return [TextContent(type="text", text="먼저 음성 채널에 입장시켜주세요 (join_voice_channel).")]

    video_url = await music_service.search_video(query)
    if not video_url:
         return [TextContent(type="text", text="음악을 찾을 수 없습니다.")]

    await music_service.add_to_queue(guild.id, video_url)
    
    # 재생 시작 (이미 재생 중이면 큐에만 추가됨)
    await music_service.play_next(guild)
    
    return [TextContent(type="text", text=f"'{query}' 검색 결과({video_url})를 재생 목록에 추가했습니다.")]

STOP_MUSIC_SCHEMA = {
    "type": "object",
    "properties": {
         "server_id": {"type": "string", "description": "서버 ID"}
    },
    "required": []
}

@tool_registry.register("stop_music", "음악 재생을 중지합니다.", STOP_MUSIC_SCHEMA)
async def stop_music(arguments: dict):
    server_id = arguments.get("server_id")
    if server_id:
        guild = await global_context.fetch_guild(int(server_id))
    else:
        msg = global_context.get_current_message()
        guild = msg.guild if msg else None
        
    if not guild: return [TextContent(type="text", text="서버 정보를 찾을 수 없습니다.")]

    success = await music_service.stop_music(guild)
    if success:
        return [TextContent(type="text", text="음악 재생을 중지했습니다.")]
    else:
        return [TextContent(type="text", text="재생 중인 음악이 없습니다.")]

SKIP_MUSIC_SCHEMA = {
    "type": "object",
    "properties": {
         "server_id": {"type": "string", "description": "서버 ID"}
    },
    "required": []
}

@tool_registry.register("skip_music", "현재 곡을 건너뜁니다.", SKIP_MUSIC_SCHEMA)
async def skip_music(arguments: dict):
    server_id = arguments.get("server_id")
    if server_id:
        guild = await global_context.fetch_guild(int(server_id))
    else:
        msg = global_context.get_current_message()
        guild = msg.guild if msg else None

    if not guild: return [TextContent(type="text", text="서버 정보를 찾을 수 없습니다.")]

    success = await music_service.skip_music(guild)
    if success:
        return [TextContent(type="text", text="다음 곡으로 넘어갑니다.")]
    else:
        return [TextContent(type="text", text="재생 중인 음악이 없습니다.")]

GET_QUEUE_SCHEMA = {
    "type": "object",
    "properties": {
         "server_id": {"type": "string", "description": "서버 ID"}
    },
    "required": []
}

@tool_registry.register("get_queue", "음악 재생 대기열을 확인합니다.", GET_QUEUE_SCHEMA)
async def get_queue(arguments: dict):
    server_id = arguments.get("server_id")
    if server_id:
        guild = await global_context.fetch_guild(int(server_id))
    else:
        msg = global_context.get_current_message()
        guild = msg.guild if msg else None

    if not guild: return [TextContent(type="text", text="서버 정보를 찾을 수 없습니다.")]

    queue = music_service.get_queue(guild.id)
    items = queue.get_list()
    
    if not items:
        return [TextContent(type="text", text="대기열이 비어있습니다.")]
        
    text = "\n".join([f"{i+1}. {url}" for i, url in enumerate(items)])
    return [TextContent(type="text", text=f"현재 대기열:\n{text}")]

