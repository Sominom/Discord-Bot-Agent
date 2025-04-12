import discord
from discord.ext import commands
from discord import app_commands
import json
import traceback
from core.config import env
from services.database import db
from services.claude import image_generate

class AICommands(commands.Cog):
    """AI 관련 서비스 명령어"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="image", description="DALL-E를 사용하여 이미지를 생성합니다")
    @app_commands.describe(
        prompt="이미지 생성을 위한 프롬프트",
        size="이미지 크기 (0: 정사각형, 1: 가로, 2: 세로)"
    )
    @app_commands.choices(size=[
        app_commands.Choice(name="정사각형", value=0),
        app_commands.Choice(name="가로 방향", value=1),
        app_commands.Choice(name="세로 방향", value=2)
    ])
    async def generate_image(self, interaction: discord.Interaction, prompt: str, size: int = 0):
        """DALL-E를 사용하여 이미지를 생성합니다"""
        await interaction.response.defer(thinking=True)
        
        try:
            # 이미지 생성 함수 호출
            await image_generate(prompt, size, interaction.followup)
        except Exception as err:
            traceback.print_exc()
            await interaction.followup.send(f"이미지 생성 중 오류가 발생했습니다: {str(err)}")

async def setup(bot):
    await bot.add_cog(AICommands(bot)) 