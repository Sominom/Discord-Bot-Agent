import os
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, EmptyResult
from mcp.server.stdio import stdio_server

# 디스코드 관련 import
import discord
from discord.ext import commands

# 로깅 설정
logger = logging.getLogger("discord-mcp-server")

# MCP 서버 초기화
mcp_app = Server("discord-server")

# 디스코드 클라이언트 참조 저장
discord_client = None

def set_discord_client(client):
    """디스코드 클라이언트 설정"""
    global discord_client
    discord_client = client
    logger.info(f"디스코드 클라이언트 설정 완료: {client.user.name if client else None}")

@mcp_app.list_tools()
async def list_tools_impl() -> List[Tool]:
    """사용 가능한 디스코드 도구 목록 반환"""
    return [
        # 검색 도구 추가
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
        # 서버 정보 도구
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

        # 역할 관리 도구
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

        # 채널 관리 도구
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

        # 메시지 반응 도구
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
        )
    ]

@mcp_app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """디스코드 도구 호출 처리"""
    global discord_client
    
    # 디버깅을 위해 입력 인자 로깅
    logger.info(f"도구 호출: {name}, 인자: {arguments}")
    
    if not discord_client:
        logger.error("디스코드 클라이언트가 준비되지 않았습니다.")
        return [TextContent(
            type="text",
            text="디스코드 클라이언트가 준비되지 않았습니다."
        )]
    
    # 필수 파라미터 검증
    missing_params = []
    try:
        tools = await list_tools_impl()
        target_tool = None
        
        # 호출된 도구 스키마 찾기
        for tool in tools:
            if tool.name == name:
                target_tool = tool
                break
        
        # 필수 파라미터 검증
        if target_tool and hasattr(target_tool, 'inputSchema') and target_tool.inputSchema:
            schema = target_tool.inputSchema
            if 'required' in schema and isinstance(schema['required'], list):
                for req_param in schema['required']:
                    if req_param not in arguments:
                        missing_params.append(req_param)
        
        if missing_params:
            logger.error(f"도구 {name} 호출 시 필수 파라미터 누락: {missing_params}")
            return [TextContent(
                type="text",
                text=f"도구 실행에 필요한 필수 파라미터가 누락되었습니다: {', '.join(missing_params)}"
            )]
    except Exception as e:
        logger.error(f"파라미터 검증 중 오류: {str(e)}")
        # 파라미터 검증에 실패하더라도 실행 시도
    
    try:
        if name == "search_and_crawl":
            from services.web import search_and_crawl
            keyword = arguments["keyword"]
            logger.info(f"검색 요청: {keyword}")
            
            # 검색 및 크롤링 실행
            result = await search_and_crawl(keyword)
            
            if result:
                # 결과가 너무 길면 truncate
                if len(result) > 4000:
                    result = result[:4000] + "... (결과가 너무 길어 일부만 표시합니다)"
                
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
                logger.info(f"get_server_id_from_message 호출: message_id={message_id}")
                
                if not message_id:
                    # 메시지 ID가 없는 경우 간단히 처리
                    logger.info("메시지 ID가 제공되지 않았습니다.")
                    return [TextContent(
                        type="text",
                        text="메시지 ID가 필요합니다."
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
                            logger.error(f"메시지 조회 오류: {str(e)}")
                            continue
                
                # 메시지를 찾지 못한 경우
                return [TextContent(
                    type="text",
                    text=f"메시지 ID {message_id}를 찾을 수 없습니다."
                )]
            except Exception as e:
                logger.error(f"get_server_id_from_message 오류: {str(e)}")
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

        # 서버 정보 도구
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

        # 역할 관리 도구
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

        # 채널 관리 도구
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

        elif name == "delete_channel":
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            await channel.delete(reason=arguments.get("reason", "MCP를 통해 삭제된 채널"))
            return [TextContent(
                type="text",
                text=f"채널 삭제 완료"
            )]

        # 메시지 반응 도구
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

        raise ValueError(f"알 수 없는 도구: {name}")
        
    except Exception as e:
        logger.error(f"도구 호출 오류: {str(e)}")
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
    """사용 가능한 도구 목록 반환"""
    # 직접 리스트 도구 핸들러 호출
    handler = mcp_app.list_tools.get_handler()
    if handler:
        return await handler()
    # 대체 방법: @app.list_tools 데코레이터로 정의된 함수 직접 호출
    return await list_tools_impl() 