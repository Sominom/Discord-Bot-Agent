from mcp_server.registry import tool_registry
from mcp_server.context import global_context
from mcp.types import TextContent
from services.web import search_and_crawl

SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "검색할 키워드"
        }
    },
    "required": ["keyword"]
}

@tool_registry.register("search_and_crawl", "구글 검색 후 크롤링한 결과를 반환합니다", SEARCH_SCHEMA)
async def search_tool(arguments: dict):
    keyword = arguments["keyword"]
    
    # 검색 및 크롤링 실행
    result = await search_and_crawl(keyword)
    
    if result:
        # 결과가 너무 길면 자름
        if len(result) > 4000:
            result = result[:4000] + "..."
        
        return [TextContent(
            type="text",
            text=f"검색 결과: {keyword}\n\n{result}"
        )]
    else:
        return [TextContent(
            type="text",
            text=f"'{keyword}'에 대한 검색 결과가 없거나 크롤링에 실패했습니다."
        )]

