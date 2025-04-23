import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, EmptyResult
from mcp.server.stdio import stdio_server
from core.logger import logger

# 디스코드 관련 import
import discord
from discord.ext import commands

# MCP 서버 초기화
mcp_app = Server("discord-server")

# 디스코드 클라이언트 참조 저장
discord_client = None
# 현재 처리 중인 메시지 객체 저장
current_message = None

def set_discord_client(client):
    
    global discord_client
    discord_client = client
    logger.log(f"디스코드 클라이언트 설정 완료: {client.user.name if client else None}", logger.INFO)

def set_current_message(message):
    
    global current_message
    current_message = message
    logger.log(f"현재 메시지 설정 완료: {message.id if message else None}", logger.INFO)

# 모든 툴 정의
def get_all_tools() -> List[Tool]:
    return [
        # 검색 툴 추가
        Tool(
            name="search_and_crawl",
            description="구글 검색 후 크롤링한 결과를 반환합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색할 키워드"
                    }
                },
                "required": ["keyword"]
            }
        ),
        # 서버 정보 툴
        Tool(
            name="get_server_info",
            description="디스코드 서버 정보 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버(길드) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="list_members",
            description="서버 멤버 목록 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "가져올 최대 멤버 수",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["server_id"]
            }
        ),

        # 역할 관리 툴
        Tool(
            name="add_role",
            description="사용자에게 역할 추가",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "역할을 추가할 사용자 ID"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "추가할 역할 ID"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),
        Tool(
            name="remove_role",
            description="사용자에게서 역할 제거",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "역할을 제거할 사용자 ID"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "제거할 역할 ID"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),

        # 채널 관리 툴
        Tool(
            name="create_text_channel",
            description="새 텍스트 채널 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "채널 이름"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "채널을 배치할 카테고리 ID (선택사항)"
                    },
                    "topic": {
                        "type": "string",
                        "description": "채널 주제 (선택사항)"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="create_voice_channel",
            description="새 음성 채널 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "채널 이름"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "채널을 배치할 카테고리 ID (선택사항)"
                    },
                    "user_limit": {
                        "type": "integer",
                        "description": "음성 채널 최대 사용자 수 (선택사항)"
                    },
                    "bitrate": {
                        "type": "integer",
                        "description": "음성 채널 비트레이트 (선택사항)"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="create_category",
            description="새 카테고리 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "카테고리 이름"
                    },
                    "position": {
                        "type": "integer",
                        "description": "카테고리 위치 (선택사항)"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="delete_category",
            description="카테고리 삭제 (포함된 채널은 삭제되지 않음)",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "삭제할 카테고리 ID"
                    }
                },
                "required": ["server_id", "category_id"]
            }
        ),
        Tool(
            name="move_channel",
            description="채널을 다른 카테고리로 이동",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "이동할 채널 ID"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "대상 카테고리 ID (비우면 카테고리 없음)"
                    }
                },
                "required": ["server_id", "channel_id"]
            }
        ),
        Tool(
            name="rename_channel",
            description="채널 이름 변경",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "변경할 채널 ID"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "새 채널 이름"
                    }
                },
                "required": ["channel_id", "new_name"]
            }
        ),
        Tool(
            name="set_slowmode",
            description="채널 슬로우 모드 설정",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "채널 ID"
                    },
                    "seconds": {
                        "type": "integer",
                        "description": "메시지 사이 간격(초)",
                        "minimum": 0,
                        "maximum": 21600
                    }
                },
                "required": ["channel_id", "seconds"]
            }
        ),
        Tool(
            name="create_invite",
            description="서버 초대 링크 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "채널 ID"
                    },
                    "max_age": {
                        "type": "integer",
                        "description": "초대 링크 유효 시간(초), 0은 무제한"
                    },
                    "max_uses": {
                        "type": "integer",
                        "description": "최대 사용 횟수, 0은 무제한"
                    },
                    "temporary": {
                        "type": "boolean",
                        "description": "임시 멤버십 여부"
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="disconnect_member",
            description="음성 채널에서 멤버 연결 끊기",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "연결 끊을 사용자 ID"
                    }
                },
                "required": ["server_id", "user_id"]
            }
        ),
        Tool(
            name="list_categories",
            description="서버의 카테고리 목록 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버 ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="delete_channel",
            description="채널 삭제",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "삭제할 채널 ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "삭제 이유"
                    }
                },
                "required": ["channel_id"]
            }
        ),

        # 메시지 반응 툴
        Tool(
            name="add_reaction",
            description="메시지에 반응 추가",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "메시지가 있는 채널 ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "반응을 추가할 메시지 ID"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "사용할 이모지 (유니코드 또는 커스텀 이모지 ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="add_multiple_reactions",
            description="메시지에 여러 반응 추가",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "메시지가 있는 채널 ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "반응을 추가할 메시지 ID"
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "사용할 이모지 (유니코드 또는 커스텀 이모지 ID)"
                        },
                        "description": "반응으로 추가할 이모지 목록"
                    }
                },
                "required": ["channel_id", "message_id", "emojis"]
            }
        ),
        Tool(
            name="remove_reaction",
            description="메시지에서 반응 제거",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "메시지가 있는 채널 ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "반응을 제거할 메시지 ID"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "제거할 이모지 (유니코드 또는 커스텀 이모지 ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="send_message",
            description="특정 채널에 메시지 전송",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "디스코드 채널 ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "메시지 내용"
                    }
                },
                "required": ["channel_id", "content"]
            }
        ),
        Tool(
            name="get_server_id_from_message",
            description="메시지에서 서버 ID를 자동으로 추출합니다.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string", "description": "메시지 ID (선택 사항)"}},
                "required": []
            }
        ),
        Tool(
            name="read_messages",
            description="채널에서 최근 메시지 읽기",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "디스코드 채널 ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "가져올 메시지 수 (최대 100)",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="get_user_info",
            description="디스코드 사용자 정보 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "디스코드 사용자 ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="moderate_message",
            description="메시지 삭제 및 선택적으로 사용자 타임아웃",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "메시지가 있는 채널 ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "처리할 메시지 ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "처리 이유"
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "타임아웃 시간(분)",
                        "minimum": 0,
                        "maximum": 40320  # 최대 4주
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),
        Tool(
            name="judge_conversation_ending",
            description="메시지가 대화를 종료하는 내용인지 판단하고 적절한 이모지로 응답합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_content": {
                        "type": "string",
                        "description": "분석할 메시지 내용"
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "메시지가 있는 채널 ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "반응을 추가할 메시지 ID"
                    }
                },
                "required": ["message_content", "channel_id", "message_id"]
            }
        ),
        Tool(
            name="generate_image",
            description="DALL-E를 사용하여 이미지를 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "이미지를 생성할 프롬프트 (영어로 입력)"
                    },
                    "size": {
                        "type": "integer",
                        "description": "이미지 사이즈 (0: 정사각형, 1: 가로 방향, 2: 세로 방향)",
                        "enum": [0, 1, 2]
                    }
                },
                "required": ["prompt", "size"]
            }
        ),
        Tool(
            name="search_channel",
            description="서버 내에서 채널 이름으로 채널을 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "검색할 디스코드 서버 ID"
                    },
                    "channel_name": {
                        "type": "string",
                        "description": "검색할 채널 이름 (일부 또는 전체)"
                    }
                },
                "required": ["server_id", "channel_name"]
            }
        ),
        Tool(
            name="get_channel_info",
            description="채널 ID로 채널의 상세 정보를 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "정보를 조회할 채널 ID"
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="set_channel_topic",
            description="텍스트 채널의 주제(토픽)를 설정합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "주제를 설정할 텍스트 채널 ID"
                    },
                    "topic": {
                        "type": "string",
                        "description": "설정할 새로운 주제 내용"
                    }
                },
                "required": ["channel_id", "topic"]
            }
        ),
        Tool(
            name="create_role",
            description="서버에 새로운 역할을 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "역할을 생성할 서버 ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "새 역할의 이름"
                    },
                    "permissions": {
                        "type": "string",
                        "description": "역할에 부여할 권한 값 (discord.Permissions 정수 값, 선택사항)"
                    },
                    "colour": {
                        "type": "string",
                        "description": "역할 색상 (헥스 코드, 예: '#FF0000', 선택사항)"
                    },
                    "hoist": {
                        "type": "boolean",
                        "description": "온라인 멤버 목록에 별도 표시 여부 (선택사항)"
                    },
                    "mentionable": {
                        "type": "boolean",
                        "description": "역할을 멘션할 수 있는지 여부 (선택사항)"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="delete_role",
            description="서버에서 역할을 삭제합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "역할을 삭제할 서버 ID"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "삭제할 역할 ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "삭제 이유 (선택사항)"
                    }
                },
                "required": ["server_id", "role_id"]
            }
        ),
        Tool(
            name="change_nickname",
            description="서버 내 사용자의 닉네임을 변경합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "닉네임을 변경할 서버 ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "닉네임을 변경할 사용자 ID"
                    },
                    "nickname": {
                        "type": "string",
                        "description": "새로운 닉네임 (비워두면 닉네임 제거)"
                    }
                },
                "required": ["server_id", "user_id", "nickname"]
            }
        ),
        Tool(
            name="kick_member",
            description="서버에서 멤버를 추방합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "멤버를 추방할 서버 ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "추방할 사용자 ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "추방 이유 (선택사항)"
                    }
                },
                "required": ["server_id", "user_id"]
            }
        ),
        Tool(
            name="ban_member",
            description="서버에서 멤버를 차단합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "멤버를 차단할 서버 ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "차단할 사용자 ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "차단 이유 (선택사항)"
                    },
                    "delete_message_days": {
                        "type": "integer",
                        "description": "차단 시 삭제할 메시지 기간(일) (0-7, 선택사항, 기본값 0)",
                        "minimum": 0,
                        "maximum": 7
                    }
                },
                "required": ["server_id", "user_id"]
            }
        ),
        Tool(
            name="send_embed",
            description="지정된 채널에 임베드 메시지를 전송합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "메시지를 보낼 디스코드 채널 ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "임베드의 제목"
                    },
                    "description": {
                        "type": "string",
                        "description": "임베드의 본문 내용"
                    },
                    "color": {
                        "type": "string",
                        "description": "임베드 색상 (헥스 코드, 예: '#FF0000', 선택사항)"
                    },
                    "footer": {
                        "type": "string",
                        "description": "임베드 푸터 텍스트 (선택사항)"
                    }
                },
                "required": ["channel_id", "title", "description"]
            }
        ),
        Tool(
            name="get_image_from_message",
            description="특정 메시지에서 이미지를 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "메시지가 있는 채널 ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "이미지가 포함된 메시지 ID"
                    }
                },
                "required": ["channel_id", "message_id"]
            }
        ),
    ]


# GPT Function 정의
def get_gpt_functions():
    return [
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

async def get_claude_tools():
    # MCP 서버에서 툴 목록 가져오기
    tools = await list_tools()
    claude_tools = []
    
    for tool in tools:
        claude_tool = {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        }
        claude_tools.append(claude_tool)
    
    return claude_tools

# 메시지 객체에서 메시지 ID, 채널 ID, 서버 ID를 추출
def extract_message_info(message=None):
    global current_message
    
    # 파라미터로 받은 메시지가 없으면 현재 저장된 메시지 사용
    message = message or current_message
    
    if not message:
        logger.log("메시지 객체가 없어 정보를 추출할 수 없습니다.", logger.ERROR)
        return None, None, None
    
    message_id = str(message.id)
    channel_id = str(message.channel.id)
    server_id = str(message.guild.id) if message.guild else None
    
    logger.log(f"메시지 정보 추출: message_id={message_id}, channel_id={channel_id}, server_id={server_id}", logger.INFO)
    
    return message_id, channel_id, server_id

# 툴 입력에 자동으로 메시지, 채널, 서버 ID 정보 추가
def auto_fill_message_info(arguments, tool_name=None):
    message_id, channel_id, server_id = extract_message_info()
    
    # 인자가 없거나 메시지 정보가 없는 경우 처리
    if not arguments:
        arguments = {}
    
    if not message_id and not channel_id and not server_id:
        logger.log("자동 메시지 정보 주입 실패: 추출된 정보 없음", logger.ERROR)
        return arguments
    
    # 메시지 ID 필드가 필요하고 비어있으면 추가
    if "message_id" in str(arguments) and not arguments.get("message_id"):
        arguments["message_id"] = message_id
    
    # 채널 ID 필드가 필요하고 비어있으면 추가
    if "channel_id" in str(arguments) and not arguments.get("channel_id"):
        arguments["channel_id"] = channel_id
    
    # 서버 ID 필드가 필요하고 비어있으면 추가
    if "server_id" in str(arguments) and not arguments.get("server_id"):
        arguments["server_id"] = server_id
    
    logger.log(f"인자 자동 주입 완료: {arguments}", logger.INFO)
    return arguments

@mcp_app.list_tools()
async def list_tools_impl() -> List[Tool]:
    return get_all_tools()

@mcp_app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    global discord_client
    
    logger.log(f"툴 호출: {name}, 인자: {arguments}", logger.INFO)
    
    if not discord_client:
        logger.log("디스코드 클라이언트가 준비되지 않았습니다.", logger.ERROR)
        return [TextContent(
            type="text",
            text="디스코드 클라이언트가 준비되지 않았습니다."
        )]
    
    missing_params = []
    try:
        tools = await list_tools_impl()
        target_tool = None
        
        # 호출된 툴 스키마 찾기
        for tool in tools:
            if tool.name == name:
                target_tool = tool
                break
        
        # 메시지, 채널, 서버 ID 자동 주입
        arguments = auto_fill_message_info(arguments, name)
        
        # 필수 파라미터 검증
        if target_tool and hasattr(target_tool, 'inputSchema') and target_tool.inputSchema:
            schema = target_tool.inputSchema
            if 'required' in schema and isinstance(schema['required'], list):
                for req_param in schema['required']:
                    if req_param not in arguments:
                        missing_params.append(req_param)
        
        if missing_params:
            logger.log(f"툴 {name} 호출 시 필수 파라미터 누락: {missing_params}", logger.ERROR)
            return [TextContent(
                type="text",
                text=f"툴 실행에 필요한 필수 파라미터가 누락되었습니다: {', '.join(missing_params)}"
            )]
    except Exception as e:
        logger.log(f"파라미터 검증 중 오류: {str(e)}", logger.ERROR)
    
    try:
        if name == "search_and_crawl":
            from services.web import search_and_crawl
            keyword = arguments["keyword"]
            logger.log(f"검색 요청: {keyword}", logger.INFO)
            
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
        
        elif name == "send_message":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            message = await channel.send(arguments["content"])
            return [TextContent(
                type="text",
                text=f"메시지 전송 완료. 메시지 ID: {message.id}"
            )]

        elif name == "send_embed":
            channel_id = arguments["channel_id"]
            title = arguments["title"]
            description = arguments["description"]
            color_hex = arguments.get("color") # 선택적 값
            footer_text = arguments.get("footer") # 선택적 값

            # 채널 객체 가져오기
            channel = await discord_client.fetch_channel(int(channel_id))

            # 임베드 생성
            embed = discord.Embed(title=title, description=description)

            # 색상 설정
            if color_hex:
                try:
                    embed.color = discord.Colour.from_str(color_hex)
                except ValueError:
                    logger.log(f"잘못된 색상 코드: {color_hex}. 기본 색상을 사용합니다.", logger.WARNING)
                    embed.color = discord.Colour.default() # 기본 색상 사용

            # 푸터 설정
            if footer_text:
                embed.set_footer(text=footer_text)

            # 임베드 전송
            message = await channel.send(embed=embed)

            # 결과 반환
            return [TextContent(
                type="text",
                text=f"임베드 메시지 전송 완료. 메시지 ID: {message.id}"
            )]

        elif name == "read_messages":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            limit = min(int(arguments.get("limit", 10)), 100)
            messages = []
            async for message in channel.history(limit=limit):
                reaction_data = []
                for reaction in message.reactions:
                    emoji_str = str(reaction.emoji)
                    reaction_info = {
                        "emoji": emoji_str,
                        "count": reaction.count
                    }
                    reaction_data.append(reaction_info)
                messages.append({
                    "id": str(message.id),
                    "author": str(message.author),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "reactions": reaction_data
                })
            return [TextContent(
                type="text",
                text=f"{len(messages)}개 메시지 조회 결과:\n\n" + 
                     "\n".join([
                         f"{m['author']} ({m['timestamp']}): {m['content']}\n" +
                         f"반응: {', '.join([f'{r['emoji']}({r['count']})' for r in m['reactions']]) if m['reactions'] else '없음'}"
                         for m in messages
                     ])
            )]
            
        elif name == "get_server_id_from_message":
            try:
                message_id = arguments.get("message_id")
                logger.log(f"get_server_id_from_message 호출: message_id={message_id}", logger.INFO)
                
                if not message_id:
                    # 현재 처리 중인 메시지에서 서버 ID 추출
                    _, _, server_id = extract_message_info()
                    if server_id:
                        guild = await discord_client.fetch_guild(int(server_id))
                        channel = current_message.channel
                        return [TextContent(
                            type="text",
                            text=f"서버 ID: {server_id}, 서버 이름: {guild.name}, 채널: {channel.name}"
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text="현재 메시지에서 서버 ID를 추출할 수 없습니다."
                        )]
                
                # 메시지가 어느 채널에서 왔는지 찾기 위해 모든 서버와 채널을 조회하는 대신,
                # 전달된 메시지의 채널과 서버 정보를 직접 활용합니다
                for message_obj in discord_client.cached_messages:
                    if message_obj.id == int(message_id):
                        guild = message_obj.guild
                        channel = message_obj.channel
                        server_id = str(guild.id)
                        return [TextContent(
                            type="text",
                            text=f"서버 ID: {server_id}, 서버 이름: {guild.name}, 채널: {channel.name}"
                        )]
                
                # 캐시에서 메시지를 찾지 못한 경우, 기존 방식으로 찾기 시도
                # 단, 아래 코드는 캐시에 메시지가 없는 경우의 폴백으로만 사용
                for guild in discord_client.guilds:
                    for channel in guild.text_channels:
                        try:
                            message = await channel.fetch_message(int(message_id))
                            server_id = str(guild.id)
                            return [TextContent(
                                type="text",
                                text=f"서버 ID: {server_id}, 서버 이름: {guild.name}, 채널: {channel.name}"
                            )]
                        except discord.NotFound:
                            continue
                        except Exception as e:
                            logger.log(f"메시지 조회 오류: {str(e)}", logger.ERROR)
                            continue
                
                # 메시지를 찾지 못한 경우
                return [TextContent(
                    type="text",
                    text=f"메시지 ID {message_id}를 찾을 수 없습니다."
                )]
            except Exception as e:
                logger.log(f"get_server_id_from_message 오류: {str(e)}", logger.ERROR)
                return [TextContent(
                    type="text",
                    text=f"서버 ID 조회 중 오류 발생: {str(e)}"
                )]

        elif name == "get_user_info":
            user = await discord_client.fetch_user(int(arguments["user_id"]))
            user_info = {
                "id": str(user.id),
                "name": user.name,
                "discriminator": user.discriminator if hasattr(user, 'discriminator') else None,
                "bot": user.bot,
                "created_at": user.created_at.isoformat()
            }
            return [TextContent(
                type="text",
                text=f"사용자 정보:\n" + 
                     f"이름: {user_info['name']}\n" +
                     f"ID: {user_info['id']}\n" +
                     f"봇 여부: {user_info['bot']}\n" +
                     f"계정 생성일: {user_info['created_at']}"
            )]

        elif name == "moderate_message":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            message = await channel.fetch_message(int(arguments["message_id"]))
            
            # 메시지 삭제
            await message.delete(reason=arguments["reason"])
            
            # 타임아웃 처리
            if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
                if isinstance(message.author, discord.Member):
                    duration = datetime.now() + datetime.timedelta(
                        minutes=arguments["timeout_minutes"]
                    )
                    await message.author.timeout(
                        duration,
                        reason=arguments["reason"]
                    )
                    return [TextContent(
                        type="text",
                        text=f"메시지 삭제 및 사용자 {arguments['timeout_minutes']}분 타임아웃 처리 완료."
                    )]
            
            return [TextContent(
                type="text",
                text="메시지 삭제 완료."
            )]

        elif name == "judge_conversation_ending":
            try:
                from services.message_judgment import is_conversation_ending
                
                # 메시지가 대화 종료 표현인지 판단
                message_content = arguments["message_content"]
                is_ending, suggested_emoji = await is_conversation_ending(message_content)
                
                # 대화 종료 메시지라면 이모지 반응 추가
                if is_ending and suggested_emoji:
                    channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
                    message = await channel.fetch_message(int(arguments["message_id"]))
                    
                    await message.add_reaction(suggested_emoji)
                    
                    # 일부 종료 메시지에 따라 다양한 이모지 추가
                    if "감사" in message_content or "고마" in message_content:
                        await message.add_reaction("❤️")
                    elif "알겠" in message_content or "알았" in message_content:
                        await message.add_reaction("✅")
                    
                    return [TextContent(
                        type="text",
                        text=f"대화 종료로 판단되어 '{suggested_emoji}' 이모지를 추가했습니다. 종료 판단: {is_ending}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"대화 종료로 판단되지 않았습니다. 종료 판단: {is_ending}"
                    )]
            except Exception as e:
                logger.log(f"대화 종료 판단 오류: {str(e)}", logger.ERROR)
                return [TextContent(
                    type="text",
                    text=f"대화 종료 판단 중 오류 발생: {str(e)}"
                )]

        # 서버 정보 툴
        elif name == "get_server_info":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            info = {
                "name": guild.name,
                "id": str(guild.id),
                "owner_id": str(guild.owner_id),
                "member_count": guild.member_count,
                "created_at": guild.created_at.isoformat(),
                "description": guild.description,
                "premium_tier": guild.premium_tier,
                "explicit_content_filter": str(guild.explicit_content_filter)
            }
            return [TextContent(
                type="text",
                text=f"서버 정보:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
            )]

        elif name == "list_members":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            limit = min(int(arguments.get("limit", 100)), 1000)
            
            members = []
            async for member in guild.fetch_members(limit=limit):
                members.append({
                    "id": str(member.id),
                    "name": member.name,
                    "nick": member.nick,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [str(role.id) for role in member.roles[1:]]  # @everyone 역할 제외
                })
            
            return [TextContent(
                type="text",
                text=f"서버 멤버 ({len(members)}명):\n" + 
                     "\n".join(f"{m['name']} (ID: {m['id']}, 역할: {', '.join(m['roles'])})" for m in members)
            )]

        # 역할 관리 툴
        elif name == "add_role":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            member = await guild.fetch_member(int(arguments["user_id"]))
            role = guild.get_role(int(arguments["role_id"]))
            
            await member.add_roles(role, reason="MCP를 통해 추가된 역할")
            return [TextContent(
                type="text",
                text=f"{member.name} 사용자에게 {role.name} 역할 추가 완료"
            )]

        elif name == "remove_role":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            member = await guild.fetch_member(int(arguments["user_id"]))
            role = guild.get_role(int(arguments["role_id"]))
            
            await member.remove_roles(role, reason="MCP를 통해 제거된 역할")
            return [TextContent(
                type="text",
                text=f"{member.name} 사용자에게서 {role.name} 역할 제거 완료"
            )]

        # 채널 관리 툴
        elif name == "create_text_channel":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            category = None
            if "category_id" in arguments:
                category = guild.get_channel(int(arguments["category_id"]))
            
            channel = await guild.create_text_channel(
                name=arguments["name"],
                category=category,
                topic=arguments.get("topic"),
                reason="MCP를 통해 생성된 채널"
            )
            
            return [TextContent(
                type="text",
                text=f"텍스트 채널 #{channel.name} (ID: {channel.id}) 생성 완료"
            )]

        elif name == "create_voice_channel":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            category = None
            if "category_id" in arguments:
                category = guild.get_channel(int(arguments["category_id"]))
            
            channel = await guild.create_voice_channel(
                name=arguments["name"],
                category=category,
                user_limit=arguments.get("user_limit"),
                bitrate=arguments.get("bitrate"),
                reason="MCP를 통해 생성된 음성 채널"
            )
            
            return [TextContent(
                type="text",
                text=f"음성 채널 🔊 {channel.name} (ID: {channel.id}) 생성 완료"
            )]

        elif name == "create_category":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            category = await guild.create_category(
                name=arguments["name"],
                position=arguments.get("position"),
                reason="MCP를 통해 생성된 카테고리"
            )
            
            return [TextContent(
                type="text",
                text=f"카테고리 📂 {category.name} (ID: {category.id}) 생성 완료"
            )]

        elif name == "delete_category":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            category = guild.get_channel(int(arguments["category_id"]))
            
            if not category or category.type != discord.ChannelType.category:
                return [TextContent(
                    type="text",
                    text=f"카테고리를 찾을 수 없거나 올바른 카테고리가 아닙니다."
                )]
                
            await category.delete(reason="MCP를 통해 삭제된 카테고리")
            return [TextContent(
                type="text",
                text=f"카테고리 '{category.name}' 삭제 완료"
            )]

        elif name == "move_channel":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            channel = guild.get_channel(int(arguments["channel_id"]))
            
            if not channel:
                return [TextContent(
                    type="text",
                    text=f"채널을 찾을 수 없습니다."
                )]
                
            category = None
            if "category_id" in arguments and arguments["category_id"]:
                category = guild.get_channel(int(arguments["category_id"]))
                if not category or category.type != discord.ChannelType.category:
                    return [TextContent(
                        type="text",
                        text=f"대상 카테고리를 찾을 수 없거나 올바른 카테고리가 아닙니다."
                    )]
            
            # 채널 이동
            await channel.edit(category=category, reason="MCP를 통해 이동된 채널")
            
            if category:
                return [TextContent(
                    type="text",
                    text=f"채널 '{channel.name}'을(를) 카테고리 '{category.name}'(으)로 이동 완료"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"채널 '{channel.name}'을(를) 카테고리 없음으로 이동 완료"
                )]

        elif name == "rename_channel":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            old_name = channel.name
            
            await channel.edit(name=arguments["new_name"], reason="MCP를 통해 이름 변경")
            
            return [TextContent(
                type="text",
                text=f"채널 이름 변경 완료: '{old_name}' → '{arguments['new_name']}'"
            )]

        elif name == "set_slowmode":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            seconds = min(max(int(arguments["seconds"]), 0), 21600)  # 0~21600초 제한
            
            await channel.edit(slowmode_delay=seconds, reason="MCP를 통해 슬로우 모드 설정")
            
            if seconds == 0:
                return [TextContent(
                    type="text",
                    text=f"채널 '{channel.name}'의 슬로우 모드가 비활성화되었습니다."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"채널 '{channel.name}'의 슬로우 모드가 {seconds}초로 설정되었습니다."
                )]

        elif name == "create_invite":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            
            max_age = arguments.get("max_age", 86400)  # 기본 24시간
            max_uses = arguments.get("max_uses", 0)  # 기본 무제한
            temporary = arguments.get("temporary", False)
            
            invite = await channel.create_invite(
                max_age=max_age,
                max_uses=max_uses,
                temporary=temporary,
                reason="MCP를 통해 생성된 초대 링크"
            )
            
            expiry_info = "무제한" if max_age == 0 else f"{max_age}초"
            usage_info = "무제한" if max_uses == 0 else f"{max_uses}회"
            
            return [TextContent(
                type="text",
                text=f"초대 링크 생성 완료: {invite.url}\n유효 기간: {expiry_info}, 최대 사용: {usage_info}, 임시 멤버십: {temporary}"
            )]

        elif name == "disconnect_member":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            member = await guild.fetch_member(int(arguments["user_id"]))
            
            if not member.voice:
                return [TextContent(
                    type="text",
                    text=f"사용자 '{member.name}'는 현재 음성 채널에 연결되어 있지 않습니다."
                )]
                
            await member.move_to(None, reason="MCP를 통해 연결 끊김")
            
            return [TextContent(
                type="text",
                text=f"사용자 '{member.name}'의 음성 채널 연결이 끊겼습니다."
            )]

        elif name == "list_categories":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            
            categories = []
            for category in guild.categories:
                channel_list = []
                for channel in category.channels:
                    channel_type = "🔊" if channel.type == discord.ChannelType.voice else "#"
                    channel_list.append(f"{channel_type} {channel.name} (ID: {channel.id})")
                
                categories.append({
                    "id": str(category.id),
                    "name": category.name,
                    "position": category.position,
                    "channels": channel_list
                })
            
            if not categories:
                return [TextContent(
                    type="text",
                    text=f"서버에 카테고리가 없습니다."
                )]
                
            # 결과 포맷팅
            result = "카테고리 목록:\n\n"
            for cat in categories:
                result += f"📂 {cat['name']} (ID: {cat['id']})\n"
                if cat['channels']:
                    for channel in cat['channels']:
                        result += f"  - {channel}\n"
                else:
                    result += "  (채널 없음)\n"
                result += "\n"
            
            return [TextContent(
                type="text",
                text=result.strip()
            )]

        elif name == "delete_channel":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            await channel.delete(reason=arguments.get("reason", "MCP를 통해 삭제된 채널"))
            return [TextContent(
                type="text",
                text=f"채널 삭제 완료"
            )]

        # 메시지 반응 툴
        elif name == "add_reaction":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            message = await channel.fetch_message(int(arguments["message_id"]))
            await message.add_reaction(arguments["emoji"])
            return [TextContent(
                type="text",
                text=f"메시지에 {arguments['emoji']} 반응 추가 완료"
            )]

        elif name == "add_multiple_reactions":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            message = await channel.fetch_message(int(arguments["message_id"]))
            for emoji in arguments["emojis"]:
                await message.add_reaction(emoji)
            return [TextContent(
                type="text",
                text=f"메시지에 반응 추가 완료: {', '.join(arguments['emojis'])}"
            )]

        elif name == "remove_reaction":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            message = await channel.fetch_message(int(arguments["message_id"]))
            await message.remove_reaction(arguments["emoji"], discord_client.user)
            return [TextContent(
                type="text",
                text=f"메시지에서 {arguments['emoji']} 반응 제거 완료"
            )]

        elif name == "search_channel":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            query = arguments["channel_name"].lower().strip()
            found_channels = []
            
            cache_guild = discord_client.get_guild(int(arguments["server_id"]))
            
            if not cache_guild:
                return [TextContent(type="text", text="서버 정보를 캐시에서 찾을 수 없습니다. 봇이 서버에 제대로 초대되었는지 확인하세요.")]
            
            # 캐시된 길드에서 채널 목록 가져오기
            channels_to_search = cache_guild.channels
            logger.log(f"채널 목록: {channels_to_search}", logger.INFO)
            
            for channel in channels_to_search:
                if query in channel.name.strip().lower():
                    channel_type_emoji = ""
                    if isinstance(channel, discord.TextChannel):
                        channel_type_emoji = "#️⃣"
                    elif isinstance(channel, discord.VoiceChannel):
                        channel_type_emoji = "🔊"
                    elif isinstance(channel, discord.CategoryChannel):
                        channel_type_emoji = "📂"
                    elif isinstance(channel, discord.StageChannel):
                        channel_type_emoji = "🎙️"
                    elif isinstance(channel, discord.ForumChannel):
                         channel_type_emoji = "📝"

                    found_channels.append({
                        "id": str(channel.id),
                        "name": channel.name,
                        "type": channel_type_emoji
                    })

            if not found_channels:
                return [TextContent(type="text", text=f"'{query}' 이름과 유사한 채널을 찾을 수 없습니다.")]
            else:
                result_text = f"'{query}' 이름으로 검색된 채널 목록:\n" + \
                              "\n".join([f"- {c['type']} {c['name']} (ID: {c['id']})" for c in found_channels])
                return [TextContent(type="text", text=result_text)]

        elif name == "get_channel_info":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            info = {
                "id": str(channel.id),
                "name": channel.name,
                "type": str(channel.type),
                "created_at": channel.created_at.isoformat(),
                "position": channel.position,
            }
            if isinstance(channel, discord.TextChannel):
                info["topic"] = channel.topic
                info["slowmode_delay"] = channel.slowmode_delay
                info["nsfw"] = channel.is_nsfw()
            elif isinstance(channel, discord.VoiceChannel):
                info["bitrate"] = channel.bitrate
                info["user_limit"] = channel.user_limit
            if hasattr(channel, 'category') and channel.category:
                info["category_id"] = str(channel.category.id)
                info["category_name"] = channel.category.name

            result_text = f"채널 정보 ({info['name']}):\n" + \
                          "\n".join([f"- {k}: {v}" for k, v in info.items()])
            return [TextContent(type="text", text=result_text)]

        elif name == "set_channel_topic":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                 return [TextContent(type="text", text="텍스트 채널만 주제를 설정할 수 있습니다.")]
            await channel.edit(topic=arguments["topic"], reason="MCP를 통해 주제 설정")
            return [TextContent(type="text", text=f"채널 #{channel.name}의 주제가 성공적으로 변경되었습니다.")]

        elif name == "create_role":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            perms_int = int(arguments.get("permissions", 0))
            permissions = discord.Permissions(perms_int)
            colour_hex = arguments.get("colour", "#000000")
            colour = discord.Colour.from_str(colour_hex)

            role = await guild.create_role(
                name=arguments["name"],
                permissions=permissions,
                colour=colour,
                hoist=arguments.get("hoist", False),
                mentionable=arguments.get("mentionable", False),
                reason="MCP를 통해 역할 생성"
            )
            return [TextContent(type="text", text=f"역할 '{role.name}' (ID: {role.id})이(가) 성공적으로 생성되었습니다.")]

        elif name == "delete_role":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            role = guild.get_role(int(arguments["role_id"]))
            if not role:
                return [TextContent(type="text", text=f"역할 ID {arguments['role_id']}를 찾을 수 없습니다.")]
            role_name = role.name
            await role.delete(reason=arguments.get("reason", "MCP를 통해 역할 삭제"))
            return [TextContent(type="text", text=f"역할 '{role_name}'이(가) 성공적으로 삭제되었습니다.")]

        elif name == "change_nickname":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            member = await guild.fetch_member(int(arguments["user_id"]))
            old_nick = member.display_name
            new_nick = arguments["nickname"] if arguments["nickname"] else None # 빈 문자열은 None으로 처리
            await member.edit(nick=new_nick, reason="MCP를 통해 닉네임 변경")
            if new_nick:
                 return [TextContent(type="text", text=f"사용자 '{old_nick}'의 닉네임이 '{new_nick}'(으)로 변경되었습니다.")]
            else:
                 return [TextContent(type="text", text=f"사용자 '{old_nick}'의 닉네임이 제거되었습니다.")]

        elif name == "kick_member":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            member = await guild.fetch_member(int(arguments["user_id"]))
            member_name = member.display_name
            await guild.kick(member, reason=arguments.get("reason", "MCP를 통해 추방됨"))
            return [TextContent(type="text", text=f"멤버 '{member_name}'(이)가 서버에서 추방되었습니다.")]

        elif name == "ban_member":
            guild = await discord_client.fetch_guild(int(arguments["server_id"]))
            # fetch_user 사용: 서버에 없어도 ID로 차단 가능
            user = await discord_client.fetch_user(int(arguments["user_id"]))
            user_name = user.display_name
            delete_days = int(arguments.get("delete_message_days", 0))
            await guild.ban(
                user,
                reason=arguments.get("reason", "MCP를 통해 차단됨"),
                delete_message_days=delete_days
            )
            return [TextContent(type="text", text=f"사용자 '{user_name}'(이)가 서버에서 차단되었습니다. (메시지 {delete_days}일치 삭제)")]

        elif name == "send_embed":
            # 입력값 가져오기
            channel_id = arguments["channel_id"]
            title = arguments["title"]
            description = arguments["description"]
            color_hex = arguments.get("color") # 선택적 값
            footer_text = arguments.get("footer") # 선택적 값

            # 채널 객체 가져오기
            channel = await discord_client.fetch_channel(int(channel_id))

            # 임베드 생성
            embed = discord.Embed(title=title, description=description)

            # 색상 설정 (제공된 경우)
            if color_hex:
                try:
                    embed.color = discord.Colour.from_str(color_hex)
                except ValueError:
                    logger.log(f"잘못된 색상 코드: {color_hex}. 기본 색상을 사용합니다.", logger.WARNING)
                    embed.color = discord.Colour.default() # 기본 색상 사용

            # 푸터 설정 (제공된 경우)
            if footer_text:
                embed.set_footer(text=footer_text)

            # 임베드 전송
            message = await channel.send(embed=embed)

            # 결과 반환
            return [TextContent(
                type="text",
                text=f"임베드 메시지 전송 완료. 메시지 ID: {message.id}"
            )]

        elif name == "get_image_from_message":
            try:
                channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
                message = await channel.fetch_message(int(arguments["message_id"]))
                
                if not message.attachments:
                    return [TextContent(
                        type="text",
                        text="메시지에 첨부된 이미지가 없습니다."
                    )]
                
                image_urls = []
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        image_urls.append({
                            "url": attachment.url,
                            "filename": attachment.filename,
                            "size": attachment.size,
                            "width": attachment.width,
                            "height": attachment.height,
                            "content_type": attachment.content_type
                        })
                
                if not image_urls:
                    return [TextContent(
                        type="text",
                        text="메시지에 이미지 형식의 첨부 파일이 없습니다."
                    )]
                
                return [TextContent(
                    type="text",
                    text=f"메시지에서 {len(image_urls)}개의 이미지를 찾았습니다:\n" + 
                         "\n".join([f"- {img['filename']} ({img['width']}x{img['height']}): {img['url']}" for img in image_urls])
                )]
            except discord.NotFound:
                return [TextContent(
                    type="text",
                    text="메시지나 채널을 찾을 수 없습니다."
                )]
            except Exception as e:
                logger.log(f"이미지 가져오기 오류: {str(e)}", logger.ERROR)
                return [TextContent(
                    type="text",
                    text=f"이미지 가져오기 중 오류 발생: {str(e)}"
                )]

        raise ValueError(f"알 수 없는 툴: {name}")
        
    except discord.Forbidden:
         logger.log(f"권한 오류: 툴 '{name}' 실행에 필요한 권한이 없습니다.", logger.ERROR)
         return [TextContent(type="text", text=f"오류: 툴 '{name}' 실행에 필요한 권한이 부족합니다.")]
    except discord.HTTPException as e:
         logger.log(f"디스코드 API 오류 ({e.status}): {e.text}", logger.ERROR)
         return [TextContent(type="text", text=f"디스코드 API 오류 발생: {e.text}")]
    except Exception as e:
        logger.log(f"툴 호출 오류: {str(e)}", logger.ERROR)
        return [TextContent(
            type="text",
            text=f"오류 발생: {str(e)}"
        )]

# MCP 서버 실행 함수
async def run_mcp_server():
    async with stdio_server() as (read_stream, write_stream):
        await mcp_app.run(
            read_stream,
            write_stream,
            mcp_app.create_initialization_options()
        )

# 내보낼 함수 추가
async def list_tools() -> List[Tool]:
    return await list_tools_impl()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_server())