from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp_server.permissions import admin_required
from mcp.types import TextContent
import discord
from datetime import datetime, timedelta
from core.logger import logger

SEND_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "디스코드 채널 ID"},
        "content": {"type": "string", "description": "메시지 내용"}
    },
    "required": ["channel_id", "content"]
}

@tool_registry.register("send_message", "특정 채널에 메시지 전송", SEND_MESSAGE_SCHEMA)
async def send_message(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    message = await channel.send(arguments["content"])
    return [TextContent(
        type="text",
        text=f"메시지 전송 완료. 메시지 ID: {message.id}"
    )]

SEND_EMBED_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "메시지를 보낼 디스코드 채널 ID"},
        "title": {"type": "string", "description": "임베드의 제목"},
        "description": {"type": "string", "description": "임베드의 본문 내용"},
        "color": {"type": "string", "description": "임베드 색상 (헥스 코드, 예: '#FF0000', 선택사항)"},
        "footer": {"type": "string", "description": "임베드 푸터 텍스트 (선택사항)"}
    },
    "required": ["channel_id", "title", "description"]
}

@tool_registry.register("send_embed", "지정된 채널에 임베드 메시지를 전송합니다.", SEND_EMBED_SCHEMA)
async def send_embed(arguments: dict):
    channel_id = arguments["channel_id"]
    title = arguments["title"]
    description = arguments["description"]
    color_hex = arguments.get("color") # 선택적 값
    footer_text = arguments.get("footer") # 선택적 값

    # 채널 객체 가져오기
    channel = await global_context.fetch_channel(int(channel_id))

    # 임베드 생성
    embed = discord.Embed(title=title, description=description)

    # 색상 설정
    if color_hex:
        try:
            embed.color = discord.Colour.from_str(color_hex)
        except ValueError:
            logger.log(f"잘못된 색상 코드: {color_hex}. 기본 색상을 사용합니다.", logger.WARNING)
            embed.color = discord.Colour.default() # 기본 색상 사용

    # 푸터 설정
    if footer_text:
        embed.set_footer(text=footer_text)

    # 임베드 전송
    message = await channel.send(embed=embed)

    # 결과 반환
    return [TextContent(
        type="text",
        text=f"임베드 메시지 전송 완료. 메시지 ID: {message.id}"
    )]

READ_MESSAGES_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "디스코드 채널 ID"},
        "limit": {"type": "number", "description": "가져올 메시지 수 (최대 100)", "minimum": 1, "maximum": 100}
    },
    "required": ["channel_id"]
}

@tool_registry.register("read_messages", "채널에서 최근 메시지 읽기", READ_MESSAGES_SCHEMA)
async def read_messages(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    limit = min(int(arguments.get("limit", 10)), 100)
    messages = []
    async for message in channel.history(limit=limit):
        reaction_data = []
        for reaction in message.reactions:
            emoji_str = str(reaction.emoji)
            reaction_info = {
                "emoji": emoji_str,
                "count": reaction.count
            }
            reaction_data.append(reaction_info)
        messages.append({
            "id": str(message.id),
            "author": str(message.author),
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
            "reactions": reaction_data
        })
    lines = []
    for m in messages:
        reactions_str = ", ".join(
            [f"{r['emoji']}({r['count']})" for r in m["reactions"]]
        ) if m["reactions"] else "없음"
        lines.append(
            f"{m['author']} ({m['timestamp']}): {m['content']}\n반응: {reactions_str}"
        )

    return [
        TextContent(
            type="text",
            text=f"{len(messages)}개 메시지 조회 결과:\n\n" + "\n".join(lines),
        )
    ]


MODERATE_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "메시지가 있는 채널 ID"},
        "message_id": {"type": "string", "description": "처리할 메시지 ID"},
        "reason": {"type": "string", "description": "처리 이유"},
        "timeout_minutes": {"type": "number", "description": "타임아웃 시간(분)", "minimum": 0, "maximum": 40320}
    },
    "required": ["channel_id", "message_id", "reason"]
}

@tool_registry.register("moderate_message", "메시지 삭제 및 선택적으로 사용자 타임아웃", MODERATE_MESSAGE_SCHEMA)
@admin_required
async def moderate_message(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    message = await channel.fetch_message(int(arguments["message_id"]))
    
    # 메시지 삭제
    await message.delete(reason=arguments["reason"])
    
    # 타임아웃 처리
    if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
        if isinstance(message.author, discord.Member):
            duration = datetime.now() + timedelta(minutes=arguments["timeout_minutes"])
            await message.author.timeout(duration, reason=arguments["reason"])
            return [TextContent(
                type="text",
                text=f"메시지 삭제 및 사용자 {arguments['timeout_minutes']}분 타임아웃 처리 완료."
            )]
    
    return [TextContent(type="text", text="메시지 삭제 완료.")]

GET_IMAGE_FROM_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "메시지가 있는 채널 ID"},
        "message_id": {"type": "string", "description": "이미지가 포함된 메시지 ID"}
    },
    "required": ["channel_id", "message_id"]
}

@tool_registry.register("get_image_from_message", "특정 메시지에서 이미지를 가져옵니다.", GET_IMAGE_FROM_MESSAGE_SCHEMA)
async def get_image_from_message(arguments: dict):
    try:
        channel = await global_context.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        if not message.attachments:
            return [TextContent(type="text", text="메시지에 첨부된 이미지가 없습니다.")]
        
        image_urls = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_urls.append({
                    "url": attachment.url,
                    "filename": attachment.filename,
                    "size": attachment.size,
                    "width": attachment.width,
                    "height": attachment.height,
                    "content_type": attachment.content_type
                })
        
        if not image_urls:
            return [TextContent(type="text", text="메시지에 이미지 형식의 첨부 파일이 없습니다.")]
        
        return [TextContent(
            type="text",
            text=f"메시지에서 {len(image_urls)}개의 이미지를 찾았습니다:\n" + 
                    "\n".join([f"- {img['filename']} ({img['width']}x{img['height']}): {img['url']}" for img in image_urls])
        )]
    except discord.NotFound:
        return [TextContent(type="text", text="메시지나 채널을 찾을 수 없습니다.")]
    except Exception as e:
        logger.log(f"이미지 가져오기 오류: {str(e)}", logger.ERROR)
        return [TextContent(type="text", text=f"이미지 가져오기 중 오류 발생: {str(e)}")]

JUDGE_CONVERSATION_ENDING_SCHEMA = {
    "type": "object",
    "properties": {
        "message_content": {"type": "string", "description": "분석할 메시지 내용"},
        "channel_id": {"type": "string", "description": "메시지가 있는 채널 ID"},
        "message_id": {"type": "string", "description": "반응을 추가할 메시지 ID"}
    },
    "required": ["message_content", "channel_id", "message_id"]
}

@tool_registry.register("judge_conversation_ending", "메시지가 대화를 종료하는 내용인지 판단하고 적절한 이모지로 응답합니다", JUDGE_CONVERSATION_ENDING_SCHEMA)
async def judge_conversation_ending(arguments: dict):
    try:
        message_content = arguments["message_content"]
        ending_keywords = [
            "알겠어", "알겠습니다", "알았어", "알았습니다", "고마워", "감사합니다", "감사해요",
            "ㄱㅅ", "ㄱㅅㅇ", "ㄱㅅㅎㄴㄷ", "땡큐", "ㅌㅋ", "OK", "오케이", "ㅇㅋ", "ㅇㅋㅇㅋ",
            "멋있다", "잘했어", "수고해", "수고했어", "그래", "그렇구나", "응", "넵", "네"
        ]
        
        is_ending = any(keyword in message_content.lower() for keyword in ending_keywords)
        suggested_emoji = "👍" if is_ending else None
        
        if is_ending and suggested_emoji:
            channel = await global_context.fetch_channel(int(arguments["channel_id"]))
            message = await channel.fetch_message(int(arguments["message_id"]))
            
            await message.add_reaction(suggested_emoji)
            
            if "감사" in message_content or "고마" in message_content:
                await message.add_reaction("❤️")
            elif "알겠" in message_content or "알았" in message_content:
                await message.add_reaction("✅")
            
            return [TextContent(
                type="text",
                text=f"대화 종료로 판단되어 '{suggested_emoji}' 이모지를 추가했습니다. 종료 판단: {is_ending}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"대화 종료로 판단되지 않았습니다. 종료 판단: {is_ending}"
            )]
    except Exception as e:
        logger.log(f"대화 종료 판단 오류: {str(e)}", logger.ERROR)
        return [TextContent(type="text", text=f"대화 종료 판단 중 오류 발생: {str(e)}")]

ADD_REACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "채널 ID"},
        "message_id": {"type": "string", "description": "메시지 ID"},
        "emoji": {"type": "string", "description": "이모지"}
    },
    "required": ["channel_id", "message_id", "emoji"]
}

@tool_registry.register("add_reaction", "메시지에 반응 추가", ADD_REACTION_SCHEMA)
async def add_reaction(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    message = await channel.fetch_message(int(arguments["message_id"]))
    await message.add_reaction(arguments["emoji"])
    return [TextContent(
        type="text",
        text=f"메시지에 {arguments['emoji']} 반응 추가 완료"
    )]

ADD_MULTIPLE_REACTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "메시지가 있는 채널 ID"},
        "message_id": {"type": "string", "description": "반응을 추가할 메시지 ID"},
        "emojis": {
            "type": "array",
            "items": {"type": "string", "description": "이모지"},
            "description": "반응으로 추가할 이모지 목록"
        }
    },
    "required": ["channel_id", "message_id", "emojis"]
}

@tool_registry.register("add_multiple_reactions", "메시지에 여러 반응 추가", ADD_MULTIPLE_REACTIONS_SCHEMA)
async def add_multiple_reactions(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    message = await channel.fetch_message(int(arguments["message_id"]))
    for emoji in arguments["emojis"]:
        await message.add_reaction(emoji)
    return [TextContent(
        type="text",
        text=f"메시지에 반응 추가 완료: {', '.join(arguments['emojis'])}"
    )]

REMOVE_REACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "메시지가 있는 채널 ID"},
        "message_id": {"type": "string", "description": "반응을 제거할 메시지 ID"},
        "emoji": {"type": "string", "description": "제거할 이모지"}
    },
    "required": ["channel_id", "message_id", "emoji"]
}

@tool_registry.register("remove_reaction", "메시지에서 반응 제거", REMOVE_REACTION_SCHEMA)
async def remove_reaction(arguments: dict):
    channel = await global_context.fetch_channel(int(arguments["channel_id"]))
    message = await channel.fetch_message(int(arguments["message_id"]))
    client = global_context.get_client()
    await message.remove_reaction(arguments["emoji"], client.user)
    return [
        TextContent(
            type="text",
            text=f"메시지에서 {arguments['emoji']} 반응 제거 완료",
        )
    ]


LIST_RECENT_BOT_MESSAGES_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {
            "type": "string",
            "description": "메시지를 조회할 채널 ID (없으면 현재 메시지의 채널 사용)",
        },
        "limit": {
            "type": "integer",
            "description": "가져올 최근 봇 메시지 수 (최대 20)",
            "minimum": 1,
            "maximum": 20,
        },
    },
    "required": [],
}


@tool_registry.register(
    "list_recent_bot_messages",
    "현재 채널에서 최근 봇 메시지 목록을 조회하여 메시지 ID와 함께 요약을 제공합니다.",
    LIST_RECENT_BOT_MESSAGES_SCHEMA,
)
async def list_recent_bot_messages(arguments: dict):
    """최근 봇 메시지들을 요약해서 보여줘서, 사용자가 편집할 메시지를 고를 수 있게 해주는 툴."""
    client = global_context.get_client()
    channel_id = arguments.get("channel_id")

    if channel_id:
        channel = await global_context.fetch_channel(int(channel_id))
    else:
        current_msg = global_context.get_current_message()
        if not current_msg:
            return [TextContent(type="text", text="현재 메시지 컨텍스트를 찾을 수 없습니다.")]
        channel = current_msg.channel

    limit = int(arguments.get("limit", 10))
    limit = max(1, min(limit, 20))

    results = []
    async for msg in channel.history(limit=100):
        if not msg.author.bot:
            continue
        if client and msg.author.id != client.user.id:
            # 다른 봇이 보낸 메시지는 제외
            continue

        content = msg.content or ""
        # 너무 길면 앞부분만 표시
        if len(content) > 80:
            content = content[:77] + "..."

        results.append(
            {
                "id": str(msg.id),
                "created_at": msg.created_at.isoformat(),
                "content_preview": content,
            }
        )

        if len(results) >= limit:
            break

    if not results:
        return [
            TextContent(
                type="text",
                text="최근 봇 메시지를 찾을 수 없습니다. (현재 채널 기준)",
            )
        ]

    lines = []
    for idx, m in enumerate(results, start=1):
        lines.append(
            f"[{idx}] ID={m['id']} ({m['created_at']}): {m['content_preview']}"
        )

    return [
        TextContent(
            type="text",
            text="최근 봇 메시지 목록입니다. 편집하고 싶은 메시지의 ID를 선택하세요:\n\n"
            + "\n".join(lines),
        )
    ]


EDIT_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {
            "type": "string",
            "description": "편집할 메시지가 있는 채널 ID (없으면 현재 메시지의 채널 사용)",
        },
        "message_id": {
            "type": "string",
            "description": "편집할 대상 메시지 ID",
        },
        "new_content": {
            "type": "string",
            "description": "새로운 메시지 내용",
        },
    },
    "required": ["message_id", "new_content"],
}

# 메시지 편집 이력 저장소 (메모리)
_edit_history = {}
_last_edited_id = None

@tool_registry.register(
    "edit_message",
    "지정한 메시지의 내용을 새 텍스트로 수정합니다.",
    EDIT_MESSAGE_SCHEMA,
)
async def edit_message(arguments: dict):
    """특정 메시지 내용을 새 텍스트로 교체하는 툴."""
    global _last_edited_id
    
    channel_id = arguments.get("channel_id")
    message_id = arguments["message_id"]
    new_content = arguments["new_content"]

    if channel_id:
        channel = await global_context.fetch_channel(int(channel_id))
    else:
        current_msg = global_context.get_current_message()
        if not current_msg:
            return [TextContent(type="text", text="현재 메시지 컨텍스트를 찾을 수 없습니다.")]
        channel = current_msg.channel

    try:
        target_msg = await channel.fetch_message(int(message_id))
    except discord.NotFound:
        return [TextContent(type="text", text="해당 메시지를 찾을 수 없습니다.")]

    # 수정 전 원본 저장
    _edit_history[target_msg.id] = target_msg.content
    _last_edited_id = target_msg.id

    await target_msg.edit(content=new_content)

    return [
        TextContent(
            type="text",
            text=f"메시지(ID={message_id}) 내용을 성공적으로 수정했습니다. (이전 내용은 저장됨)",
        )
    ]

UNDO_EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "채널 ID (선택)"},
        "message_id": {"type": "string", "description": "되돌릴 메시지 ID (생략 시 가장 최근에 수정한 메시지)"}
    },
    "required": []
}

@tool_registry.register(
    "undo_edit_message",
    "최근 수정한 메시지를 수정 전 원래 내용으로 되돌립니다.",
    UNDO_EDIT_SCHEMA
)
async def undo_edit_message(arguments: dict):
    global _last_edited_id
    
    target_id = arguments.get("message_id")
    if not target_id:
        if not _last_edited_id:
            return [TextContent(type="text", text="최근 수정 이력이 없습니다.")]
        target_id = str(_last_edited_id)
        
    target_id_int = int(target_id)
    
    if target_id_int not in _edit_history:
        return [TextContent(type="text", text=f"메시지 ID {target_id}의 이전 버전을 찾을 수 없습니다.")]
        
    original_content = _edit_history[target_id_int]
    
    # 채널 찾기
    channel_id = arguments.get("channel_id")
    if channel_id:
        channel = await global_context.fetch_channel(int(channel_id))
    else:
        msg = global_context.get_current_message()
        if msg:
            channel = msg.channel
        else:
             return [TextContent(type="text", text="채널 정보를 찾을 수 없습니다. channel_id를 입력해주세요.")]

    try:
        target_msg = await channel.fetch_message(target_id_int)
        await target_msg.edit(content=original_content)
        
        # 복원 후 이력에서 삭제? 아니면 유지? -> 유지하는 게 안전 (Redo는 없지만)
        # _last_edited_id는 그대로 두거나 갱신. 여기선 그대로 둠.
        
        return [TextContent(type="text", text=f"메시지(ID={target_id})를 수정 전 상태로 복원했습니다.")]
    except discord.NotFound:
        return [TextContent(type="text", text="해당 메시지가 삭제되어 복원할 수 없습니다.")]
    except Exception as e:
        return [TextContent(type="text", text=f"복원 중 오류 발생: {str(e)}")]
