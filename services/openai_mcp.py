import datetime
import json
import traceback
from typing import Any, Dict, List, Optional, Tuple

import discord

from openai import AsyncOpenAI

from core.config import env
from core.logger import logger
from mcp_server import call_tool, get_openai_mcp_tools, set_current_message
from services.prompts import system_prompts

from services.database import get_setting

_openai_client = None


def get_openai_client() -> AsyncOpenAI:
    """OpenAI 비동기 클라이언트 싱글톤 인스턴스 반환"""
    global _openai_client
    if _openai_client is None:
        try:
            _openai_client = AsyncOpenAI(api_key=env.OPENAI_API_KEY)
            logger.log("OpenAI 비동기 클라이언트 초기화 완료")
        except Exception as e:
            logger.log(f"OpenAI 클라이언트 초기화 실패: {str(e)}", logger.ERROR)
            raise
    return _openai_client


async def image_generate(prompt: str, size: int, reply_message: discord.Message):
    """DALL·E 이미지를 생성하고 응답 메시지를 업데이트합니다."""
    sizestr = ["1024x1024", "1792x1024", "1024x1792"][size]

    try:
        prompt_for_api = prompt if len(prompt) <= 1000 else f"{prompt[:997]}..."
        await reply_message.edit(content="이미지를 생성하는 중... 잠시만 기다려주세요.")

        openai_client = get_openai_client()
        response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt_for_api,
            n=1,
            size=sizestr,
        )

        for image in response.data:
            try:
                embed = create_image_embed(prompt, prompt, image.url)
                await reply_message.edit(content="이미지를 생성했습니다.", embed=embed)
                return
            except discord.HTTPException as exc:
                logger.log(f"임베드 전송 오류: {str(exc)}", logger.ERROR)
                await reply_message.edit(content=f"이미지를 생성했습니다.\n이미지 URL: {image.url}")
                return

        await reply_message.edit(content="이미지 생성 결과가 없습니다.")
    except Exception as err:
        traceback.print_exc()
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


async def update_discord_message(message: discord.Message, current_text: str, force: bool = False, last_update_length: int = 0):
    """디스코드 메시지를 일정 간격으로 업데이트합니다."""
    # 빈 메시지 방지
    if not current_text:
        current_text = ". . ."
        
    if len(current_text) - last_update_length >= 200 or force:
        last_update_length = len(current_text)

        if len(current_text) > 1900:
            current_text = f"{current_text[:1900]}..."

        await message.edit(content=current_text)
        return last_update_length

    return last_update_length


def _get_max_response_tokens() -> int:
    return getattr(env, "MAX_RESPONSE_TOKENS", 2000)


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
    initial_conversation = await _build_initial_conversation(message, username, prompt, img_mode, img_url)
    return [*base_prompts, *initial_conversation]


async def _ensure_reply_message(message: discord.Message, message_object: Optional[discord.Message]) -> discord.Message:
    return message_object or await message.reply("...")


def _parse_tool_arguments(arguments: Optional[str]) -> Dict[str, Any]:
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as exc:
        # 스트리밍 중에는 불완전한 JSON일 수 있으므로 경고 로그는 생략하고 빈 딕셔너리 반환 또는 재시도
        # 여기서는 일단 빈 딕셔너리 반환
        return {}


async def _handle_tool_call(
    tool_call: Any,
    reply_message: discord.Message,
    latest_text_response: str,
    message_id: int,
) -> Optional[Dict[str, Any]]:
    # 이 함수는 이제 스트리밍 로직 내에서 직접 처리되지 않고, 툴 실행 결과만 반환하는 역할로 축소되거나 변경될 수 있음.
    # 하지만 기존 로직을 재활용하기 위해 유지하되, 메시지 업데이트 로직은 상위 레벨에서 제어함.
    
    tool_name = tool_call.function.name
    tool_args_str = tool_call.function.arguments
    
    # 스트리밍에서 완성된 arguments 파싱
    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError:
        tool_args = {}

    tool_result = await execute_tool(tool_name, tool_args, message_id)

    if tool_result["type"] == "image_generation":
        await image_generate(tool_result["prompt"], tool_result["size"], reply_message)
        tool_content = f"이미지 생성 완료: '{tool_result['prompt']}'"
    elif tool_result["type"] == "error":
        return None # 상위에서 처리
    else:
        tool_content = tool_result["content"]

    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": tool_content,
    }


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
    reply_message = await _ensure_reply_message(message, message_object)

    try:
        max_tool_rounds = 50
        current_round = 0
        
        # 디스코드에 표시된 최종 텍스트 (툴 메시지 제외)
        display_text = ""
        last_update_length = 0

        openai_tools = await get_openai_mcp_tools()
        client = get_openai_client()

        while current_round < max_tool_rounds:
            current_round += 1

            response = await client.chat.completions.create(
                model=env.OPENAI_MODEL,
                messages=messages,
                max_completion_tokens=_get_max_response_tokens(),
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
                    last_update_length = await update_discord_message(
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
                await update_discord_message(reply_message, temp_display_text, force=True)
                
                for tc in tool_calls_list:
                    # 가짜 객체 생성 (호환성 유지)
                    class ToolCallObj:
                        def __init__(self, d):
                            self.id = d['id']
                            self.type = d['type']
                            self.function = type('Function', (), {'name': d['function']['name'], 'arguments': d['function']['arguments']})
                            
                    tool_obj = ToolCallObj(tc)
                    
                    # 툴 실행 (UI 업데이트 로직은 위에서 일괄 처리했으므로 내부에서는 결과만 받음)
                    # 기존 _handle_tool_call 함수를 조금 수정하거나 여기서 직접 호출
                    # 여기서는 직접 호출하여 메시지 수정을 제어함
                    
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
                
                await update_discord_message(reply_message, display_text, force=True)
                
                # 최대 툴 호출 체크
                if current_round == max_tool_rounds:
                    logger.log("최대 툴 호출 도달", logger.WARNING)
                    display_text += "\n\n[최대 툴 호출 횟수에 도달했습니다.]"
                    await update_discord_message(reply_message, display_text, force=True)
                    break
                    
            else:
                # 툴 호출이 없으면 대화 종료
                messages.append(assistant_msg)
                
                # 마지막으로 강제 업데이트 (남은 텍스트 표시)
                await update_discord_message(reply_message, display_text, force=True)
                
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


def create_image_embed(title: str, description: str, url: str):
    
    # 제목 길이 제한 (임베드 title 최대 256자)
    if len(title) > 250:
        title = title[:247] + "..."
    
    # 설명 길이 제한 (디스코드 임베드 description 최대 4096자)
    if len(description) > 4000:
        description = description[:3997] + "..."
    
    embed = discord.Embed(
        title=title,
        description=description,
    )
    embed.set_thumbnail(url=url)
    embed.set_image(url=url)
    return embed


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

async def is_message_for_bot(message_content: str, username: str, bot_name: str, recent_messages: List[dict] = None) -> Tuple[bool, float]:
    try:
        # 메시지 컨텍스트 구성
        context = ""
        if recent_messages:
            for msg in recent_messages:
                author = "봇" if msg["is_bot"] else msg["author"]
                context += f"{author}: {msg['content']}\n"
        
        # OpenAI API 요청
        openai_client = get_openai_client()
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini", # 모델명도 수정 (4.1-nano 등은 없는 모델일 수 있음)
            messages=[
                {"role": "system", "content": f"당신은 메시지가 봇에게 보내는 것인지 판단하는 AI입니다. 최근 대화 맥락과 메시지 내용을 분석하여 메시지가 '{bot_name}'에게 보내는 것인지 판단하세요."},
                {"role": "user", "content": f"최근 대화 맥락:\n{context}\n\n사용자 '{username}'의 새 메시지: {message_content}\n\n이 메시지가 봇('{bot_name}')에게 보내는 것인지 판단하세요. JSON 형식으로 다음을 반환하세요: {{\"is_for_bot\": true/false, \"confidence\": 0~1, \"reason\": \"판단 이유\"}}"}
            ],
        )
        
        # 응답 추출
        result_text = response.choices[0].message.content
        try:
            result = json.loads(result_text)
            is_for_bot = result.get("is_for_bot", False)
            confidence = result.get("confidence", 0)
            return is_for_bot, confidence
        except json.JSONDecodeError:
            logger.log(f"JSON 파싱 오류: {result_text}", logger.ERROR)
            return False, 0
    except Exception as e:
        logger.log(f"메시지 판단 오류: {str(e)}", logger.ERROR)
        return False, 0