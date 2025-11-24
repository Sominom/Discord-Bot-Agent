import discord
from discord.ext import commands
import traceback
import asyncio
from core.logger import logger
from core.config import env
from mcp_server.server import MCPServer
from mcp_server.context import global_context

# 봇 클래스 정의
class InteractiveGPTBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=[], intents=intents)
        self.logger = logger
        self.initial_extensions = [
            'cogs.app_commands',
            'cogs.chat_commands',
            'cogs.ai_commands'
        ]
        
        # MCP 서버 인스턴스 생성
        self.mcp_server = MCPServer()

        # 봇 소유자 ID 설정
        self.owner_id = env.DISCORD_OWNER_ID
        if self.owner_id:
            self.logger.log(f'봇 소유자 ID 설정: {self.owner_id}')
        else:
            self.logger.log('DISCORD_OWNER_ID가 설정되지 않았습니다.', self.logger.WARNING)

    async def setup_hook(self):
        # 확장 기능(Cogs) 로드
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                self.logger.log(f'확장 기능 로드: {extension}')
            except Exception as e:
                self.logger.log(f'확장 기능 로드 실패: {extension}\n{str(e)}', self.logger.ERROR)
                traceback.print_exc()
        
        # MCP 서버 시작 (백그라운드 태스크)
        self.logger.log('MCP 서버 시작 준비...')
        self.loop.create_task(self.mcp_server.start())
        
        # 글로벌 명령어 동기화
        try:
            self.logger.log('글로벌 명령어 동기화 시작')
            synced_commands = await self.tree.sync()
            self.logger.log(f'글로벌 명령어 동기화 완료: {len(synced_commands)}개 명령어 동기화됨')
        except Exception as e:
            self.logger.log(f'글로벌 명령어 동기화 실패: {str(e)}', self.logger.ERROR)
            traceback.print_exc()
        

    async def on_ready(self):
        self.logger.log(f'{self.user} 로그인 완료')
        
        # MCP 컨텍스트에 디스코드 클라이언트 주입
        global_context.set_client(self)
        
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="대화 요청"
        ))

    async def on_connect(self):
        self.logger.log(f"{self.user} 연결 완료")

    async def on_error(self, event, *args, **kwargs):
        self.logger.log(f'이벤트 처리 중 오류 발생: {event}', self.logger.ERROR)
        traceback.print_exc()

# 봇 실행
if __name__ == "__main__":
    bot = InteractiveGPTBot()
    bot_key = env.DISCORD_BOT_KEY
    
    if not bot_key:
        logger.log("DISCORD_BOT_KEY가 설정되지 않았습니다. 봇을 실행할 수 없습니다.", logger.CRITICAL)
    else:
        logger.log(f"봇 실행 시작", logger.INFO)
        bot.run(bot_key)
