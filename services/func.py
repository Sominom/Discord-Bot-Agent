import discord
from discord.ext import commands
from core.config import env
from services.database import get_setting

def create_image_embed(title: str, description: str, url: str):
    
    # 제목 길이 제한 (임베드 title 최대 256자)
    if len(title) > 250:
        title = title[:247] + "..."
    
    # 설명 길이 제한 (디스코드 임베드 description 최대 4096자)
    if len(description) > 4000:
        description = description[:3997] + "..."
    
    embed = discord.Embed(
        title=title,
        description=description,
    )
    embed.set_thumbnail(url=url)
    embed.set_image(url=url)
    return embed


async def prompt_to_chat(message, username, prompt):
    conversation = []

    history_num_str = get_setting("history_num")
    if history_num_str and history_num_str.isdigit():
        history_num = int(history_num_str)
    else:
        history_num = env.HISTORY_NUM
    
    # 채널의 이전 메시지를 가져옴
    async for chat in message.channel.history(limit=history_num):
        # 현재 메시지는 제외
        if chat.id == message.id:
            continue
            
        user = chat.author
        server_name = user.nick
        if server_name is None:
            server_name = user.name
            
        # 봇 메시지와 사용자 메시지를 프롬프트 형식으로 변환
        if user.bot and message.guild and user.id == message.guild.me.id:
            conversation.append({"role": "assistant", "content": f"{chat.content}"})
        else:
            # 이미지가 있는 경우 별도 표시
            if chat.attachments:
                conversation.append({"role": "user", "content": f"{server_name}: [사진] {chat.content}"})
            else:
                conversation.append({"role": "user", "content": f"{server_name}: {chat.content}"})
                
    # 최신 메시지가 먼저 오도록 순서 반전
    conversation = conversation[::-1]
    # 현재 메시지 추가
    conversation.append({"role": "user", "content": f"{username}: {prompt}"})
    
    return conversation