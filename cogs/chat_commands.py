import discord
from discord.ext import commands
import traceback
from discord import app_commands
from services.gpt import chat
from core.config import env
from services.database import db

class ChatCommands(commands.Cog):
    """사용자 메시지 처리 및 GPT 응답 관련 명령어"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # 봇의 메시지는 무시
        if message.author.bot:
            return
        
        # 채팅 채널이 아닌 경우 무시
        channel = message.channel
        
        # 데이터베이스에서 채팅 채널 확인
        chat_channels = db.get_chat_channels()
        if channel.id not in chat_channels:
            return
            
        # 빈 메시지 무시
        text = message.content
        if text == "":
            return
            
        # 시스템 메시지인 경우 무시
        if message.type != discord.MessageType.default:
            return
            
        # 이미지 처리
        image_mode = False
        image_url = ""
        try:
            if message.attachments:
                image_mode = True
                image_url = message.attachments[0].url
        except Exception:
            pass
            
        # 메시지 처리
        user = message.author
        
        async with channel.typing():
            try:
                # 닉네임이 없으면 유저명 사용
                server_name = user.nick
                if server_name is None:
                    server_name = user.name
                    
                # GPT에 메시지 전달 (message 객체와 필요한 정보 전달)
                await chat(message, server_name, text, image_mode, image_url)
            except Exception as err:
                # message.reply 사용하여 응답
                await message.reply(f"에러입니다.\n{str(err)}")
                traceback.print_exc()
    
    @app_commands.command(name="clear", description="채팅 방을 청소합니다")
    @app_commands.guild_only()
    async def clear_chat(self, interaction: discord.Interaction, amount: int = 100):
        """채팅방 메시지를 청소합니다"""
        if interaction.channel is None:
            await interaction.response.send_message("유효한 채널이 아닙니다.", ephemeral=True)
            return
            
        # 권한 확인
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("메시지 관리 권한이 필요합니다.", ephemeral=True)
            return
            
        await interaction.response.send_message(f"{amount}개의 메시지를 삭제합니다...", ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"{len(deleted)}개의 메시지가 삭제되었습니다.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChatCommands(bot)) 