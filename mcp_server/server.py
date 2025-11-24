import asyncio
import pkgutil
import importlib
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from core.logger import logger
from mcp_server.registry import tool_registry
from mcp_server.context import global_context
import mcp_server.tools

class MCPServer:
    def __init__(self, name: str = "discord-server"):
        self.app = Server(name)
        self.load_tools()
        self.setup_handlers()

    def load_tools(self):
        """mcp_server.tools 패키지 내의 모든 모듈을 자동으로 로드합니다."""
        package = mcp_server.tools
        prefix = package.__name__ + "."

        for _, name, _ in pkgutil.iter_modules(package.__path__, prefix):
            try:
                importlib.import_module(name)
                logger.log(f"MCP 툴 모듈 로드: {name}", logger.INFO)
            except Exception as e:
                logger.log(f"MCP 툴 모듈 로드 실패 ({name}): {e}", logger.ERROR)

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
