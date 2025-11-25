import datetime
import json
import traceback
from typing import Any, Dict, List, Optional, Tuple

import discord

from core.config import env
from core.logger import logger
from mcp_server import call_tool, get_openai_mcp_tools, set_current_message
from services.prompts import system_prompts, assistant_prompts_start
from services.database import get_setting
from services.ai_service import ai_service
from services.discord_service import discord_service
from services.music_service import music_service

async def image_generate(prompt: str, size: int, reply_message: discord.Message):
    """DALL·E 이미지를 생성하고 응답 메시지를 업데이트합니다."""
    sizestr = ["1024x1024", "1792x1024", "1024x1792"][size]

    try:
        await reply_message.edit(content="이미지를 생성하는 중... 잠시만 기다려주세요.")

        images = await ai_service.generate_image(prompt, sizestr)

        for image in images:
            try:
                embed = discord_service.create_image_embed(prompt, prompt, image.url)
                await reply_message.edit(content="이미지를 생성했습니다.", embed=embed)
                return
            except discord.HTTPException as exc:
                logger.log(f"임베드 전송 오류: {str(exc)}", logger.ERROR)
                await reply_message.edit(content=f"이미지를 생성했습니다.\n이미지 URL: {image.url}")
                return

        await reply_message.edit(content="이미지 생성 결과가 없습니다.")
    except Exception as err:
        logger.log(f"이미지 생성 중 오류: {err}", logger.ERROR)
        await _fallback_image_error(reply_message, err)


async def _fallback_image_error(reply_message: discord.Message, err: Exception):
    try:
        await reply_message.edit(content=f"이미지를 생성하는데 오류가 발생했습니다.\n오류: {str(err)[:500]}")
    except Exception:
        try:
            await reply_message.channel.send(f"이미지 생성 오류: {str(err)[:500]}")
        except Exception:
            pass


def _serialize_tool_response(result: Any) -> str:
    if isinstance(result, list):
        parts = []
        for item in result:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(result)


async def execute_tool(tool_name: str, tool_input: Dict[str, Any], message_id: Optional[int] = None):
    """MCP 툴을 실행하고 표준화된 결과를 반환합니다."""
    tool_input = tool_input or {}

    try:
        if tool_name == "generate_image" and "prompt" in tool_input:
            return {
                "type": "image_generation",
                "prompt": tool_input["prompt"],
                "size": tool_input.get("size", 0),
            }

        if tool_name == "get_server_id_from_message" and message_id and not tool_input.get("message_id"):
            tool_input["message_id"] = str(message_id)

        result = await call_tool(tool_name, tool_input)
        formatted = _serialize_tool_response(result)

        return {
            "type": "tool_result",
            "content": formatted if formatted.strip() else f"{tool_name} 툴 실행 완료",
        }
    except Exception as exc:
        logger.log(f"툴 실행 오류: {str(exc)}", logger.ERROR)
        return {"type": "error", "message": str(exc)}


async def _build_initial_conversation(
    message: discord.Message,
    username: str,
    prompt: str,
    img_mode: bool,
    img_url: Optional[str],
) -> List[Dict[str, Any]]:
    if img_mode and img_url:
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{username}: {prompt}"},
                    {"type": "image_url", "image_url": {"url": img_url, "detail": "high"}},
                ],
            }
        ]
    return await prompt_to_chat(message, username, prompt)


def _build_system_prompts(message: discord.Message) -> List[Dict[str, Any]]:
    base_prompts = [prompt_block.copy() for prompt_block in system_prompts]
    if not base_prompts or base_prompts[0].get("role") != "system":
        return base_prompts

    base_prompts[0] = base_prompts[0].copy()
    base_prompts[0]["content"] += f"\nToday is {datetime.datetime.now().strftime('%Y-%m-%d')} A.D."

    server_id = str(message.guild.id) if message.guild else "DM"
    server_name = message.guild.name if message.guild else "DM"
    channel_id = str(message.channel.id)
    channel_name = message.channel.name if hasattr(message.channel, "name") else "Direct Message"
    user_id = str(message.author.id)
    message_id = str(message.id)

    base_prompts[0]["content"] += f"\n현재 서버: {server_name}, 채널: {channel_name}"
    base_prompts[0]["content"] += f"\ncurrent_server_id: {server_id}"
    base_prompts[0]["content"] += f"\ncurrent_channel_id: {channel_id}"
    base_prompts[0]["content"] += f"\ncurrent_user_id: {user_id}"
    base_prompts[0]["content"] += f"\ncurrent_message_id: {message_id}"

    set_current_message(message)
    return base_prompts


async def _prepare_conversation_messages(
    message: discord.Message,
    username: str,
    prompt: str,
    img_mode: bool,
    img_url: Optional[str],
) -> List[Dict[str, Any]]:
    base_prompts = _build_system_prompts(message)
    initial_conversation = await _build_initial_conversation(
        message, username, prompt, img_mode, img_url
    )

    # 과거에 이미 이런 식으로 대화를 시작했다는 느낌의 초기 어시스턴트 메시지를 붙임
    starter_prompts = assistant_prompts_start or []

    return [*base_prompts, *starter_prompts, *initial_conversation]


async def chat_with_openai_mcp(
    message: discord.Message,
    username: str,
    prompt: str,
    img_mode: bool = False,
    img_url: Optional[str] = None,
    message_object: Optional[discord.Message] = None,
):
    """OpenAI Chat Completions + MCP 툴 루프 (스트리밍 지원)."""
    messages = await _prepare_conversation_messages(message, username, prompt, img_mode, img_url)
    reply_message = await discord_service.ensure_reply_message(message, message_object)

    try:
        max_tool_rounds = 50
        current_round = 0
        
        # 디스코드에 표시된 최종 텍스트 (툴 메시지 제외)
        display_text = ""
        last_update_length = 0

        openai_tools = await get_openai_mcp_tools()
        client = ai_service.client

        while current_round < max_tool_rounds:
            current_round += 1

            response = await client.chat.completions.create(
                model=env.OPENAI_MODEL,
                messages=messages,
                max_completion_tokens=ai_service.get_max_response_tokens(),
                tools=openai_tools,
                tool_choice="auto",
                stream=True, # 스트리밍 활성화
            )
            
            # 현재 라운드에서 생성된 텍스트와 툴 호출
            current_round_text = ""
            tool_calls_buffer = {} # index -> ToolCall 조각
            
            async for chunk in response:
                delta = chunk.choices[0].delta
                
                # 1. 텍스트 처리
                if delta.content:
                    current_round_text += delta.content
                    display_text += delta.content
                    
                    # 40자 단위 업데이트 (텍스트만 표시)
                    last_update_length = await discord_service.update_message(
                        reply_message,
                        display_text,
                        last_update_length=last_update_length
                    )
                
                # 2. 툴 호출 처리 (조각 모으기)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        index = tc.index
                        if index not in tool_calls_buffer:
                            tool_calls_buffer[index] = {
                                "id": tc.id,
                                "type": tc.type or "function",
                                "function": {
                                    "name": tc.function.name or "",
                                    "arguments": tc.function.arguments or ""
                                }
                            }
                        else:
                            # 이미 존재하는 인덱스면 내용 추가
                            if tc.function.arguments:
                                tool_calls_buffer[index]["function"]["arguments"] += tc.function.arguments
            
            # 스트리밍 종료 후 처리
            
            # 완성된 텍스트를 메시지 기록에 추가
            assistant_msg = {"role": "assistant", "content": current_round_text}
            
            # 툴 호출이 있었는지 확인
            if tool_calls_buffer:
                # 툴 호출 목록 구성
                tool_calls_list = []
                sorted_indices = sorted(tool_calls_buffer.keys())
                
                for idx in sorted_indices:
                    tc_data = tool_calls_buffer[idx]
                    tool_calls_list.append({
                        "id": tc_data["id"],
                        "type": tc_data["type"],
                        "function": {
                            "name": tc_data["function"]["name"],
                            "arguments": tc_data["function"]["arguments"]
                        }
                    })
                
                assistant_msg["tool_calls"] = tool_calls_list
                messages.append(assistant_msg)
                
                logger.log(f"{len(tool_calls_list)}개 툴 호출 감지됨. 실행 시작.", logger.INFO)
                
                # 툴 실행 및 UI 표시
                tool_responses = []
                
                # 툴 사용 중 메시지 표시 (기존 텍스트 유지 + 툴 알림 추가)
                tool_names = ", ".join([tc["function"]["name"] for tc in tool_calls_list])
                temp_display_text = f"{display_text}\n\n🛠️ `{tool_names}` 도구 사용 중..."
                await discord_service.update_message(reply_message, temp_display_text, force=True)
                
                for tc in tool_calls_list:
                    # 툴 실행
                    try:
                        tool_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                        
                    tool_result = await execute_tool(tc["function"]["name"], tool_args, message.id)
                    
                    # 이미지 생성 등 특수 툴 처리
                    if tool_result["type"] == "image_generation":
                        await image_generate(tool_result["prompt"], tool_result["size"], reply_message)
                        tool_content = f"이미지 생성 완료: '{tool_result['prompt']}'"
                    elif tool_result["type"] == "error":
                        tool_content = f"툴 실행 오류: {tool_result['message']}"
                    else:
                        tool_content = tool_result["content"]
                        
                    tool_responses.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_content
                    })
                
                messages.extend(tool_responses)
                
                await discord_service.update_message(reply_message, display_text, force=True)
                
                # 최대 툴 호출 체크
                if current_round == max_tool_rounds:
                    logger.log("최대 툴 호출 도달", logger.WARNING)
                    warning_msg = "\n\n[최대 툴 호출 횟수에 도달했습니다.]"
                    display_text += warning_msg
                    
                    if len(display_text) > 2000:
                         # 2000자 초과 시 분할 전송
                        await discord_service.update_message(reply_message, display_text[:2000], force=True)
                        remaining = display_text[2000:]
                        while remaining:
                            chunk = remaining[:2000]
                            remaining = remaining[2000:]
                            await reply_message.channel.send(chunk)
                    else:
                        await discord_service.update_message(reply_message, display_text, force=True)
                    break
                    
            else:
                # 툴 호출이 없으면 대화 종료
                messages.append(assistant_msg)
                
                # 최종 업데이트
                if len(display_text) > 2000:
                    # 첫 2000자는 기존 메시지 수정
                    await discord_service.update_message(reply_message, display_text[:2000], force=True)
                    
                    # 나머지는 2000자 단위로 나누어 새 메시지로 전송
                    remaining_text = display_text[2000:]
                    while remaining_text:
                        chunk = remaining_text[:2000]
                        remaining_text = remaining_text[2000:]
                        try:
                            await reply_message.channel.send(chunk)
                        except Exception as e:
                            logger.log(f"메시지 분할 전송 실패: {str(e)}", logger.ERROR)
                            break
                else:
                    # 2000자 이하면 그냥 업데이트
                    await discord_service.update_message(reply_message, display_text, force=True)
                
                # TTS 읽기 (음성 채널에 있는 경우)
                if message.guild and message.guild.voice_client and message.guild.voice_client.is_connected():
                    # 코드 블록 등은 읽기에 불편하므로 제거하
                    # 여기서는 전체 텍스트를 넘기되, 너무 길면 music_service.tts 내부에서 끊길 수도 있음
                    # music_service.tts는 비동기(run_in_executor)로 동작하므로 블로킹하지 않음
                    await music_service.tts(message.guild, display_text)

                logger.log("툴 호출 없음, 루프 종료.", logger.INFO)
                break

    except Exception as exc:
        logger.log(f"OpenAI MCP 응답 처리 오류: {str(exc)}", logger.ERROR)
        traceback.print_exc()
        await _handle_chat_failure(message, reply_message, exc)


async def _handle_chat_failure(message: discord.Message, reply_message: discord.Message, exc: Exception):
    try:
        await reply_message.edit(content=f"오류가 발생했습니다: {str(exc)}")
    except Exception:
        await message.reply(f"오류가 발생했습니다: {str(exc)}")


async def prompt_to_chat(message, username, prompt):
    conversation = []

    history_num_str = get_setting("history_num")
    if history_num_str and history_num_str.isdigit():
        history_num = int(history_num_str)
    else:
        history_num = env.HISTORY_NUM
    
    # 채널의 이전 메시지를 가져옴
    async for chat in message.channel.history(limit=history_num):
        # 현재 메시지는 제외
        if chat.id == message.id:
            continue
            
        user = chat.author
        server_name = user.nick
        if server_name is None:
            server_name = user.name
            
        # 봇 메시지와 사용자 메시지를 프롬프트 형식으로 변환
        if user.bot and message.guild and user.id == message.guild.me.id:
            conversation.append({"role": "assistant", "content": f"{chat.content}"})
        else:
            # 이미지가 있는 경우 별도 표시
            if chat.attachments:
                conversation.append({"role": "user", "content": f"{server_name}: [사진] {chat.content}"})
            else:
                conversation.append({"role": "user", "content": f"{server_name}: {chat.content}"})
                
    # 최신 메시지가 먼저 오도록 순서 반전
    conversation = conversation[::-1]
    # 현재 메시지 추가
    conversation.append({"role": "user", "content": f"{username}: {prompt}"})
    
    return conversation

# Re-export is_message_for_bot for backward compatibility
async def is_message_for_bot(message_content: str, username: str, bot_name: str, recent_messages: List[dict] = None) -> Tuple[bool, float]:
    return await ai_service.is_message_for_bot(message_content, username, bot_name, recent_messages)