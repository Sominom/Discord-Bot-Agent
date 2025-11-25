import discord
from discord.ext import commands
from discord import app_commands
from core.config import env
from core.logger import logger
from services.database import add_chat_channel, delete_chat_channel, get_chat_channels

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="addchatchannel", description="현재 채널을 대화 채널에 추가합니다")
    @app_commands.guild_only()
    async def add_chat_channel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # 관리자 또는 봇 소유자 권한 확인
        if not (interaction.user.guild_permissions.administrator or str(interaction.user.id) in env.DISCORD_OWNER_IDS):
            await interaction.followup.send("관리자 권한이 필요합니다.")
            return
            
        channel = interaction.channel
        channel_id = channel.id
        guild_id = interaction.guild.id

        success = add_chat_channel(channel_id, guild_id, channel.name)
        
        if success:
            await interaction.followup.send(f"채널 '{channel.name}'이(가) 대화 채널로 추가되었습니다.")
        else:
            await interaction.followup.send("채널 추가 중 오류가 발생했습니다. 로그를 확인하세요.")
    
    @app_commands.command(name="removechatchannel", description="현재 채널을 대화 채널에서 제거합니다")
    @app_commands.guild_only()
    async def remove_chat_channel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # 관리자 또는 봇 소유자 권한 확인
        if not (interaction.user.guild_permissions.administrator or str(interaction.user.id) in env.DISCORD_OWNER_IDS):
            await interaction.followup.send("관리자 권한이 필요합니다.")
            return
            
        channel_id = interaction.channel.id

        success = delete_chat_channel(channel_id)
        
        if success:
            await interaction.followup.send(f"채널 '{interaction.channel.name}'이(가) 대화 채널에서 제거되었습니다.")
        else:
            await interaction.followup.send("채널 제거 중 오류가 발생했습니다. 로그를 확인하세요.")
    
    @app_commands.command(name="listchannels", description="대화 채널 목록을 표시합니다")
    @app_commands.guild_only()
    async def list_chat_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # 관리자 또는 봇 소유자 권한 확인
        if not (interaction.user.guild_permissions.administrator or str(interaction.user.id) in env.DISCORD_OWNER_IDS):
            await interaction.followup.send("관리자 권한이 필요합니다.")
            return

        channel_ids = get_chat_channels()
        
        channels = []
        for channel_id in channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel:
                channels.append(f"- {channel.name} (ID: {channel_id})")
            else:
                channels.append(f"- 알 수 없는 채널 (ID: {channel_id})")
                
        if not channels:
            await interaction.followup.send("등록된 대화 채널이 없습니다.")
            return
            
        embed = discord.Embed(
            title="대화 채널 목록",
            description="\n".join(channels),
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot)) 