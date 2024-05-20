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
                        "description": "키워드",
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
            "description": "이미지를 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "영어로 이미지를 생성할 문장을 입력하세요.",
                    },
                    "size": {
                        "type": "integer",
                        "description": "이미지 사이즈 = 0: 정사각형, 1: 가로 그림, 2: 세로 그림",
                        "enum": [0, 1, 2],
                    },
                },
                "required": ["prompt", "size"],
            },
        },
    },
]
