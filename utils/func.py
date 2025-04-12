import discord
from discord.ext import commands

from data.config import Config

config = Config()
ts = Translate()
bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

def create_image_embed(title: str, description: str, url: str):
    embed = discord.Embed(
        title=title,
        description=description,
    )
    embed.set_thumbnail(url=url)
    embed.set_image(url=url)
    return embed


async def prompt_to_chat(ctx, username, prompt):
    conversation = []
    history_num = config.history_num
    async for chat in ctx.channel.history(limit=history_num):
        if chat.id == ctx.message.id:
            continue
        user = chat.author
        server_name = user.nick
        if server_name is None:
            server_name = user.name
        if user == bot.user:
            conversation.append({"role": "assistant", "content": f"{chat.content}"})
        else:
            if chat.attachments:
                conversation.append({"role": "user", "content": f"{server_name}: [사진] {chat.content}"})
            else:
                conversation.append({"role": "user", "content": f"{server_name}: {chat.content}"})
    conversation = conversation[::-1]
    conversation.append({"role": "user", "content": f"{username}: {prompt}"})
    return conversation