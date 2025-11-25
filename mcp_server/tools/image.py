from mcp_server.registry import tool_registry
from mcp.types import TextContent

GENERATE_IMAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string", "description": "이미지를 생성할 프롬프트 (영어로 입력)"},
        "size": {"type": "integer", "description": "이미지 사이즈 (0: 정사각형, 1: 가로 방향, 2: 세로 방향)", "enum": [0, 1, 2]}
    },
    "required": ["prompt", "size"]
}

@tool_registry.register("generate_image", "DALL-E를 사용하여 이미지를 생성합니다.", GENERATE_IMAGE_SCHEMA)
async def generate_image(arguments: dict):
    # 실제 이미지 생성 로직은 openai_mcp.py에서 처리하므로 여기서는 요청 정보만 반환
    # execute_tool에서 type="image_generation"으로 처리됨
    return [TextContent(
        type="text",
        text=f"이미지 생성 요청: {arguments['prompt']}"
    )]

