import asyncio
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from core.logger import logger
from mcp_server.registry import tool_registry
from mcp_server.context import global_context

# 툴 모듈 로드 (여기서 import해야 레지스트리에 등록됩니다)
import mcp_server.tools.channel
import mcp_server.tools.message
import mcp_server.tools.search 
import mcp_server.tools.member
import mcp_server.tools.role
import mcp_server.tools.server
import mcp_server.tools.image
# 추가된 툴 모듈들을 계속 여기에 추가해야 합니다.

class MCPServer:
    def __init__(self, name: str = "discord-server"):
        self.app = Server(name)
        self.setup_handlers()

    def setup_handlers(self):
        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            return tool_registry.get_all_tools()

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            logger.log(f"MCP 툴 호출: {name}, 인자: {arguments}", logger.INFO)
            
            # 1. 툴 핸들러 찾기
            handler = tool_registry.get_handler(name)
            if not handler:
                raise ValueError(f"알 수 없는 툴: {name}")

            # 2. 컨텍스트 자동 주입 (선택사항)
            # 필요하다면 services/mcp/utils.py 등을 만들어 auto_fill 로직 구현 가능
            
            try:
                # 3. 핸들러 실행
                return await handler(arguments)
            except Exception as e:
                logger.log(f"툴 실행 중 오류 발생 ({name}): {str(e)}", logger.ERROR)
                return [TextContent(
                    type="text",
                    text=f"오류 발생: {str(e)}"
                )]

    async def start(self):
        """stdio 방식으로 서버 실행"""
        logger.log("MCP 서버 시작 (Stdio 모드)", logger.INFO)
        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(
                read_stream,
                write_stream,
                self.app.create_initialization_options()
            )
