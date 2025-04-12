import asyncio
import discord
from discord.ext import commands
from data.config import Config
from discord import app_commands
class AppCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        
    async def cog_load(self):
        self.bot.tree.add_command(app_commands.Command(
            name="addchatchannel",
            description="현재 채널을 대화 채널에 추가합니다.",
            callback=self.addchatchannel
        ))
        
        self.bot.tree.add_command(app_commands.Command(
            name="removechatchannel",
            description="현재 채널을 대화 채널에서 제거합니다.",
            callback=self.removechatchannel
        ))
        
        self.bot.tree.add_command(app_commands.Command(
            name="clear",
            description="채팅 방을 청소합니다.",
            callback=self.clear
        ))
        
        self.bot.tree.add_command(app_commands.Command(
            name="historylimit",
            description="프롬프트에 전송할 최근 대화 수를 설정합니다.",
            callback=self.historylimit
        ))
        
    
    async def addchatchannel(self, interaction: discord.Interaction):
        self.config.add_chat_channel(interaction.channel.id)
        await interaction.response.send_message(f"현재 채널이 대화 채널에 추가되었습니다: {interaction.channel}")
        
    async def removechatchannel(self, interaction: discord.Interaction):
        self.config.delete_chat_channel(interaction.channel.id)
        await interaction.response.send_message(f"현재 채널이 대화 채널에서 제거되었습니다: {interaction.channel}")
        
    async def historylimit(self, interaction: discord.Interaction, historylimit: int):
        self.config.history_num = historylimit
        await interaction.response.send_message(f"최근 대화 수를 설정했습니다: {historylimit}")

    async def clear(self, interaction: discord.Interaction):
        if interaction.channel is not None:
            await interaction.response.send_message("채팅 방을 청소합니다.")
            await interaction.channel.purge(limit=4096)
            await asyncio.sleep(1)
        return
    

async def setup(bot):
    cog = AppCommands(bot)
    await bot.add_cog(cog)
