import discord
from core.logger import logger

class DiscordService:
    @staticmethod
    async def update_message(message: discord.Message, current_text: str, force: bool = False, last_update_length: int = 0) -> int:
        """디스코드 메시지를 일정 간격으로 업데이트합니다."""
        if not current_text:
            current_text = ". . ."
            
        if len(current_text) - last_update_length >= 200 or force:
            last_update_length = len(current_text)

            if len(current_text) > 1900:
                current_text = f"{current_text[:1900]}..."

            try:
                await message.edit(content=current_text)
            except Exception as e:
                logger.log(f"메시지 업데이트 실패: {str(e)}", logger.WARNING)
            return last_update_length

        return last_update_length

    @staticmethod
    def create_image_embed(title: str, description: str, url: str) -> discord.Embed:
        if len(title) > 250:
            title = title[:247] + "..."
        
        if len(description) > 4000:
            description = description[:3997] + "..."
        
        embed = discord.Embed(
            title=title,
            description=description,
        )
        embed.set_thumbnail(url=url)
        embed.set_image(url=url)
        return embed

    @staticmethod
    async def ensure_reply_message(message: discord.Message, message_object: discord.Message = None) -> discord.Message:
        return message_object or await message.reply("...")

discord_service = DiscordService()
