import discord
from discord.ext import commands
from discord import app_commands
from services.openai_mcp import chat_with_openai_mcp
from services.openai_mcp import is_message_for_bot
from mcp_server import call_tool
from core.config import env
from services.database import get_chat_channels, get_setting
from core.logger import logger

class ChatCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 메시지 처리 임계값
        self.confidence_threshold = 0.6
    
    @commands.Cog.listener()
    async def on_message(self, message):
        logger.log(f"메시지 수신: {message.content}", logger.INFO)
        # 봇의 메시지는 무시
        if message.author.bot:
            logger.log(f"봇의 메시지이므로 무시: {message.content}", logger.INFO)
            return
        
        # 채팅 채널이 아닌 경우 무시
        channel = message.channel

        # 채팅 채널 확인
        chat_channels = get_chat_channels()
        is_chat_channel = channel.id in chat_channels
        
        # 채팅 채널이 아닌 경우, 멘션이 없으면 무시
        if not is_chat_channel:
            if not self.bot.user in message.mentions:
                logger.log(f"채팅 채널이 아니고 멘션도 아니므로 무시: {channel.name}", logger.INFO)
                return
            else:
                logger.log(f"채팅 채널은 아니지만 멘션이 있어 처리: {channel.name}", logger.INFO)
        
        # 빈 메시지 무시
        text = message.content
        if text == "":
            logger.log(f"빈 메시지이므로 무시: {text}", logger.INFO)
            return
            
        # 시스템 메시지인 경우 무시
        if message.type != discord.MessageType.default:
            logger.log(f"시스템 메시지이므로 무시: {message.type}", logger.INFO)
            return
            
        # 이미지 처리
        image_mode = False
        image_url = None
        try:
            if message.attachments:
                for attachment in message.attachments:
                    # 첨부 파일이 이미지인지 확인
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        image_mode = True
                        image_url = attachment.url
                        break
        except Exception as e:
            logger.log(f"이미지 첨부 처리 중 오류 발생: {str(e)}", logger.ERROR)
            # 오류가 발생해도 계속 진행
            
        # 메시지 처리
        user = message.author
        
        # 닉네임이 없으면 유저명 사용
        server_name = user.nick
        if server_name is None:
            server_name = user.name
                
        # 최근 메시지 5개 가져오기
        recent_messages = []
        try:
            # 현재 채널에서 최근 메시지 6개 가져오기 (현재 메시지 포함)
            async for msg in channel.history(limit=6):
                # 현재 메시지는 제외
                if msg.id == message.id:
                    continue
                
                # 시스템 메시지 제외
                if msg.type != discord.MessageType.default:
                    continue
                
                # 메시지 정보 저장
                recent_messages.append({
                    "message_id": msg.id,
                    "content": msg.content,
                    "author": msg.author.nick if msg.author.nick else msg.author.name,
                    "is_bot": msg.author.bot
                })
                
                # 최대 5개만 저장
                if len(recent_messages) >= get_setting("history_num"):
                    break
            
            # 시간 순서대로 정렬 (오래된 메시지가 먼저 오도록)
            recent_messages.reverse()
        except Exception as e:
            # 메시지 히스토리 가져오기 실패 시 무시하고 진행
            recent_messages = []
            
        # 메시지가 봇에게 보내는 것인지 판단 (OpenAI)
        is_for_bot, confidence = await is_message_for_bot(
            message_content=text,
            username=server_name,
            bot_name=self.bot.user.name,
            recent_messages=recent_messages
        )
                
        # 봇에게 보내는 메시지로 판단된 경우
        # 멘션이 있으면 무조건 응답 대상으로 간주
        should_respond = is_for_bot or confidence >= self.confidence_threshold
        if self.bot.user in message.mentions:
            should_respond = True

        if should_respond:
            # 메시지가 대화를 종료하는 내용인지 판단
            try:
                await call_tool(
                    "judge_conversation_ending",
                    {
                        "message_content": text,
                        "channel_id": str(channel.id),
                        "message_id": str(message.id),
                    },
                )
            except Exception as e:
                # MCP 도구 호출 실패 시 로그 남기고 계속 진행
                logger.log(f"judge_conversation_ending 툴 호출 실패: {str(e)}", logger.ERROR)
            
            async with channel.typing():
                try:
                    # OpenAI MCP를 사용하여 메시지 응답 (이미지 URL도 전달)
                    await chat_with_openai_mcp(message, server_name, text, image_mode, image_url)
                except Exception as err:
                    await message.reply(f"에러입니다.\n{str(err)}")
                    logger.log(f"채팅 처리 중 오류 발생: {str(err)}", logger.ERROR)
    
    @app_commands.command(name="clear", description="채팅 방을 청소합니다")
    @app_commands.guild_only()
    async def clear_chat(self, interaction: discord.Interaction, amount: int = 100):
        
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