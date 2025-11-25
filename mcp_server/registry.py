from typing import Callable, Dict, List, Any, Optional
from mcp.types import Tool
import inspect
from functools import wraps
from core.logger import logger

class ToolRegistry:
    """
    MCP 툴을 등록하고 관리하는 레지스트리입니다.
    """
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, name: str, description: str, input_schema: Dict[str, Any]):
        """
        데코레이터로 사용할 툴 등록 함수입니다.
        """
        def decorator(func: Callable):
            # 툴 메타데이터 생성
            tool = Tool(
                name=name,
                description=description,
                inputSchema=input_schema
            )
            
            self._tools[name] = tool
            self._handlers[name] = func
            
            logger.log(f"MCP 툴 등록됨: {name}", logger.DEBUG)
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def get_all_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_handler(self, name: str) -> Optional[Callable]:
        return self._handlers.get(name)

# 전역 레지스트리 인스턴스
tool_registry = ToolRegistry()

