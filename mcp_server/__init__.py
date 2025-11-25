from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp.types import TextContent

# 외부 모듈 호환성을 위한 인터페이스 제공

def set_discord_client(client):
    global_context.set_client(client)

def set_current_message(message):
    global_context.set_current_message(message)

async def call_tool(name: str, arguments: dict):
    handler = tool_registry.get_handler(name)
    if not handler:
        raise ValueError(f"알 수 없는 툴: {name}")
    
    return await handler(arguments)

def _convert_tools_to_openai_format():
    """내부 헬퍼: 툴 레지스트리를 OpenAI Function 포맷으로 변환"""
    tools = tool_registry.get_all_tools()
    openai_tools = []

    for tool in tools:
        parameters = tool.inputSchema if tool.inputSchema else {
            "type": "object",
            "properties": {}
        }
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters
            }
        })
    return openai_tools

async def get_openai_mcp_tools():
    """OpenAI Function 호출에 사용할 MCP 툴 스키마 반환 (비동기)"""
    # 레거시 코드 호환성을 위해 비동기로 유지
    return _convert_tools_to_openai_format()

def get_gpt_functions():
    """GPT 모듈용 툴 스키마 반환 (동기)"""
    return _convert_tools_to_openai_format()
