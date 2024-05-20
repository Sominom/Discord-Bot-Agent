import openai
import re
import traceback
import discord
from discord.ext import commands
from utils.gpt import chat

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)
from data.config import Config
from data.bot_logger import BotLogger

SERVER_IDS = []

config = Config()
logger = BotLogger()

forbidden_domains = config.forbidden_domains
forbidden_search_keywords = config.forbidden_search_keywords

initial_extensions = [
    'cogs.app_commands'
]

@bot.event
async def on_ready():
    for extension in initial_extensions:
        logger.log(f'Loading {extension}')
        await bot.load_extension(extension)
    await bot.tree.sync()
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_connect():
    print(f"{bot.user.name} connected.")

@bot.event
async def on_message(message):
    image_mode = False
    image_url = ""
    ctx = await bot.get_context(message)
    user = message.author
    channel = message.channel
    text = message.content
    
    # 채팅 채널이 아닌 경우 무시
    if channel.id not in config.chat_channels:
        return
    if text == "":
        return
    # 봇 자신이 보낸 메시지인 경우 무시
    if user == bot.user:
        return
    if message.author.bot:
        return
    # 시스템 메시지인 경우 무시
    if message.type != discord.MessageType.default:
        return
    try:
        if message.attachments:
            image_mode = True
            image_url = message.attachments[0].url
    except:
        pass

    async with channel.typing():
        try:
            user = ctx.author
            server_name = user.nick
            if server_name is None:
                server_name = user.name
            await chat(ctx, server_name, text, image_mode, image_url)
        except Exception as err:
            await ctx.reply(f"에러입니다.\n{str(err)}")
            traceback.print_exc()
            
bot.run(config.discord_bot_key)
