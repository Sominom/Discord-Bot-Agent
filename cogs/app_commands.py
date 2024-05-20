import asyncio
import discord
from discord.ext import commands
from data.config import Config
from discord import app_commands
from data.translate import Translate

class AppCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        self.ts = Translate()
        
    async def cog_load(self):
        self.bot.tree.add_command(app_commands.Command(
            name="addchatchannel",
            description=self.ts.text("Add the current channel to the conversation channel."),
            callback=self.addchatchannel
        ))
        
        self.bot.tree.add_command(app_commands.Command(
            name="removechatchannel",
            description=self.ts.text("Delete the current channel from the conversation channel."),
            callback=self.removechatchannel
        ))
        
        self.bot.tree.add_command(app_commands.Command(
            name="clear",
            description=self.ts.text("Cleaning the chat room"),
            callback=self.clear
        ))
        
        self.bot.tree.add_command(app_commands.Command(
            name="historylimit",
            description=self.ts.text("Number of recent conversations to send to prompts"),
            callback=self.historylimit
        ))
        
    
    async def addchatchannel(self, interaction: discord.Interaction):
        self.config.add_chat_channel(interaction.channel.id)
        await interaction.response.send_message(f"{self.ts.text('The current channel has been added to the Conversation Channel:')} {interaction.channel}")
        
    async def removechatchannel(self, interaction: discord.Interaction):
        self.config.delete_chat_channel(interaction.channel.id)
        await interaction.response.send_message(f"{self.ts.text('The current channel has been deleted from the conversation channel:')} {interaction.channel}")
        
    async def historylimit(self, interaction: discord.Interaction, historylimit: int):
        self.config.history_num = historylimit
        await interaction.response.send_message(f"{self.ts.text('Number of conversations to remember has been set:')} {historylimit}")

    async def clear(self, interaction: discord.Interaction):
        if interaction.channel is not None:
            await interaction.response.send_message(self.ts.text("I'll clean the chat room."))
            await interaction.channel.purge(limit=4096)
            await asyncio.sleep(1)
        return
    

async def setup(bot):
    cog = AppCommands(bot)
    await bot.add_cog(cog)
