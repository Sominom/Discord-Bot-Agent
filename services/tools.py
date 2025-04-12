"""
GPT 함수 호출을 위한 도구 정의 모듈
"""

# GPT 함수 정의
gpt_functions = [
    {
        "type": "function",
        "function": {
            "name": "search_and_crawl",
            "description": "구글 검색 후 크롤링한 결과를 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색할 키워드",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "image_generate",
            "description": "DALL-E를 사용하여 이미지를 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "이미지를 생성할 프롬프트 (영어로 입력)",
                    },
                    "size": {
                        "type": "integer",
                        "description": "이미지 사이즈 (0: 정사각형, 1: 가로 방향, 2: 세로 방향)",
                        "enum": [0, 1, 2],
                    },
                },
                "required": ["prompt", "size"],
            },
        },
    },
] 