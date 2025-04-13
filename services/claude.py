import os
import json
import traceback
import datetime
import re
import logging
from typing import List, Dict, Any, Optional
import asyncio
import anthropic
import discord

from services.prompts import system_prompts
from services.func import prompt_to_chat, create_image_embed
from core.config import env
from core.logger import logger

# OpenAI 클라이언트 (이미지 생성용)
from openai import OpenAI
openai_client = OpenAI(api_key=env.OPENAI_API_KEY)

# Anthropic Claude 클라이언트 초기화
claude_client = anthropic.Anthropic(api_key=env.CLAUDE_API_KEY)

async def image_generate(prompt: str, size: int, reply_message: discord.Message):
    
    sizestr = ["1024x1024", "1792x1024", "1024x1792"][size]

    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=sizestr
        )
        data: list = response.data
        for index, image in enumerate(data):
            title = f"{prompt}"
            embed = create_image_embed(title, prompt, image.url)
        await reply_message.edit(content=f"이미지를 생성했습니다. {prompt}", embed=embed)
    except Exception as err:
        traceback.print_exc()
        await reply_message.edit(content=f"이미지를 생성하는데 오류가 발생했습니다. {str(err)}")

async def get_claude_response(messages: List[Dict[str, Any]], tools=None) -> Any:
    
    try:
        # 시스템 프롬프트 추출
        system_prompt = None
        filtered_messages = []
        
        # 시스템 메시지가 있으면 시스템 프롬프트로 추가
        for msg in messages:
            if msg["role"] == "system":
                if system_prompt is None:
                    system_prompt = msg["content"]
                else:
                    system_prompt += "\n" + msg["content"]
            else:
                filtered_messages.append(msg)

        # 스트리밍 모드로 호출
        response = claude_client.messages.create(
            model=env.CLAUDE_MODEL,
            system=system_prompt,
            messages=filtered_messages,
            temperature=0.7,
            max_tokens=2000,
            tools=tools,
            stream=True
        )
        return response
    except Exception as e:
        logger.log(f"Claude API 호출 오류: {str(e)}", logger.ERROR)
        traceback.print_exc()
        return {"error": str(e)}

async def extract_tool_info(message_chunks, tool_name=None):
    
    tool_info = {
        "id": None,
        "name": tool_name,
        "input": {}
    }
    
    text_content = ""
    
    for chunk in message_chunks:
        # 텍스트 누적
        if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'type') and chunk.delta.type == 'text_delta':
            if hasattr(chunk.delta, 'text'):
                text_content += chunk.delta.text
        
        # 도구 사용 델타에서 정보 추출
        if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'tool_use'):
            # ID 추출
            if hasattr(chunk.delta.tool_use, 'id'):
                tool_info["id"] = chunk.delta.tool_use.id
            
            # 이름 추출
            if hasattr(chunk.delta.tool_use, 'name'):
                tool_info["name"] = chunk.delta.tool_use.name
            
            # 입력 정보 추출
            if hasattr(chunk.delta.tool_use, 'input'):
                if isinstance(chunk.delta.tool_use.input, dict):
                    tool_info["input"].update(chunk.delta.tool_use.input)
                elif chunk.delta.tool_use.input:
                    try:
                        if isinstance(chunk.delta.tool_use.input, str):
                            input_data = json.loads(chunk.delta.tool_use.input)
                            if isinstance(input_data, dict):
                                tool_info["input"].update(input_data)
                    except:
                        logger.log(f"JSON 파싱 오류: {chunk.delta.tool_use.input}", logger.WARNING)
        
        # content_block에서 정보 추출
        if hasattr(chunk, 'content_block') and hasattr(chunk.content_block, 'type') and chunk.content_block.type == 'tool_use':
            if hasattr(chunk.content_block, 'id'):
                tool_info["id"] = chunk.content_block.id
            if hasattr(chunk.content_block, 'name'):
                tool_info["name"] = chunk.content_block.name
            if hasattr(chunk.content_block, 'input') and chunk.content_block.input:
                if isinstance(chunk.content_block.input, dict):
                    tool_info["input"].update(chunk.content_block.input)
                elif isinstance(chunk.content_block.input, str):
                    try:
                        input_data = json.loads(chunk.content_block.input)
                        if isinstance(input_data, dict):
                            tool_info["input"].update(input_data)
                    except:
                        logger.log(f"콘텐츠 블록 JSON 파싱 오류: {chunk.content_block.input}", logger.WARNING)
    
    # 입력 정보가 없는 경우 텍스트에서 추출 시도
    if not tool_info["input"]:
        try:
            # JSON 패턴 검색
            json_pattern = r'```json\s*({.*?})\s*```'
            json_match = re.search(json_pattern, text_content, re.DOTALL)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    if isinstance(json_data, dict):
                        tool_info["input"].update(json_data)
                        logger.log(f"텍스트에서 JSON 입력 추출: {json_data}", logger.INFO)
                except:
                    logger.log(f"텍스트 JSON 파싱 오류: {json_match.group(1)}", logger.WARNING)
            
            # 특수 도구 처리
            if tool_info["name"] == "get_server_id_from_message" and "message_id" not in tool_info["input"]:
                # message_id 추가가 외부에서 이루어질 것임
                logger.log("get_server_id_from_message 도구 감지됨", logger.INFO)
            elif tool_info["name"] == "generate_image" and not tool_info["input"]:
                prompt_match = re.search(r'이미지.생성.*?["\']([^"\']+)["\']', text_content)
                if prompt_match:
                    prompt_text = prompt_match.group(1)
                    tool_info["input"] = {"prompt": prompt_text, "size": 0}
                    logger.log(f"텍스트에서 이미지 프롬프트 추출: {prompt_text}", logger.INFO)
        except Exception as e:
            logger.log(f"텍스트에서 정보 추출 오류: {str(e)}", logger.ERROR)
    
    logger.log(f"최종 도구 정보: {tool_info}", logger.INFO)
    return tool_info, text_content

async def execute_tool(tool_name, tool_input, message_id=None):
    
    try:
        # 특수 도구 처리
        if tool_name == "generate_image" and "prompt" in tool_input:
            # 이미지 생성은 직접 처리하지 않고 호출자에게 반환
            return {"type": "image_generation", "prompt": tool_input["prompt"], "size": tool_input.get("size", 0)}
        
        # get_server_id_from_message 처리 시 자동으로 message_id 추가
        if tool_name == "get_server_id_from_message" and message_id and "message_id" not in tool_input:
            tool_input["message_id"] = str(message_id)
            logger.log(f"message_id 자동 추가: {message_id}", logger.INFO)
        
        # MCP 모듈을 통해 도구 호출
        from services.mcp import call_tool
        result = await call_tool(tool_name, tool_input)
        
        # 결과 처리
        if result:
            logger.log(f"{tool_name} 도구 실행 결과: {result}", logger.INFO)
            return {"type": "tool_result", "result": result}
        else:
            return {"type": "error", "message": "도구 실행 결과가 없습니다."}
    except Exception as e:
        logger.log(f"도구 실행 오류: {str(e)}", logger.ERROR)
        return {"type": "error", "message": str(e)}

async def update_discord_message(message, current_text, force=False, last_update_length=0):
    
    if len(current_text) - last_update_length >= 40 or force:
        last_update_length = len(current_text)
        
        # 메시지 길이가 1900자를 초과하면 자르기
        if len(current_text) > 1900:
            current_text = current_text[:1900] + "..."
        
        await message.edit(content=current_text)
        return last_update_length
    
    return last_update_length

async def process_tool_result(tool_result_content, server_id=None):
    
    # 주로 get_server_id_from_message 결과 처리를 위한 함수
    if server_id:
        return server_id
    
    # 텍스트에서 서버 ID 추출 시도
    try:
        if "서버 ID:" in tool_result_content:
            match = re.search(r"서버 ID:\s*(\d+)", tool_result_content)
            if match:
                extracted_id = match.group(1)
                logger.log(f"도구 결과에서 서버 ID 추출: {extracted_id}", logger.INFO)
                return extracted_id
    except Exception as e:
        logger.log(f"서버 ID 추출 오류: {str(e)}", logger.ERROR)
    
    return None

async def process_tool_in_conversation(messages, tool_info, tool_result_content):
    
    # 서버 ID 추출 및 결과 처리
    server_id = await process_tool_result(tool_result_content)
    
    tool_use_message = {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": tool_info["id"],
                "name": tool_info["name"],
                "input": tool_info["input"]
            }
        ]
    }
    
    tool_result = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_info["id"],
                "content": tool_result_content
            }
        ]
    }
    
    # 새로운 메시지 구성
    new_messages = messages + [tool_use_message, tool_result]
    return new_messages, server_id

async def chat_with_claude(message, username, prompt, img_mode=False, img_url=None, message_object=None):
    # 이미지 모드인 경우 처리
    if img_mode:
        initial_conversation = []
        initial_conversation.append({"role": "user", "content": [
            {"type": "text", "text": f"{username}: {prompt}"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_url}}
        ]})
    else:
        # 대화 기록 가져오기
        initial_conversation = await prompt_to_chat(message, username, prompt)

    # 기본 시스템 프롬프트 가져오기
    base_prompts = system_prompts.copy()
    
    # 첫 번째 시스템 프롬프트에 정보 추가
    if base_prompts and base_prompts[0]["role"] == "system":
        # 날짜 정보
        base_prompts[0]["content"] += f"\nToday is {datetime.datetime.now().strftime('%Y-%m-%d')} A.D."
        
        # 서버 정보
        server_id = str(message.guild.id) if message.guild else "DM"
        server_name = message.guild.name if message.guild else "DM"
        channel_id = str(message.channel.id)
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "Direct Message"
        user_id = str(message.author.id)
        message_id = str(message.id)
        
        # 서버, 채널, 사용자, 메시지 정보 추가
        base_prompts[0]["content"] += f"\n현재 서버: {server_name}, 채널: {channel_name}"
        base_prompts[0]["content"] += f"\ncurrent_server_id: {server_id}"
        base_prompts[0]["content"] += f"\ncurrent_channel_id: {channel_id}"
        base_prompts[0]["content"] += f"\ncurrent_user_id: {user_id}"
        base_prompts[0]["content"] += f"\ncurrent_message_id: {message_id}"
        
        # MCP 관련 모듈 설정
        from services.mcp import set_current_message
        set_current_message(message)
    
    # MCP 도구 가져오기
    from services.mcp import get_claude_tools
    mcp_tools = await get_claude_tools()
    
    # 초기 메시지 구성
    messages = [
        *base_prompts,
        *initial_conversation
    ]

    # 메시지 객체가 없는 경우 새로 생성
    if not message_object:
        reply_message = await message.reply(". . .")
    else:
        reply_message = message_object
        
    try:
        max_tool_rounds = 50
        current_round = 0
        latest_text_response = ""

        while current_round < max_tool_rounds:
            current_round += 1

            # 시스템 프롬프트 분리 및 메시지 필터링
            system_prompt = None
            filtered_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = (system_prompt + "\n" + msg["content"]) if system_prompt else msg["content"]
                else:
                    filtered_messages.append(msg)

            # Claude API 호출
            logger.log(f"Claude API 호출 ({current_round}) 시작", logger.INFO)
            response = claude_client.messages.create(
                model=env.CLAUDE_MODEL,
                system=system_prompt,
                messages=filtered_messages,
                temperature=0.7,
                max_tokens=8000, # 기존 설정 유지
                tools=mcp_tools
            )
            logger.log(f"Claude API 호출 ({current_round}) 완료", logger.INFO)

            # 응답 처리
            assistant_response_content = [] # 전체 응답 블록 저장
            tool_calls_in_response = []
            text_in_response = ""
            has_text = False

            for block in response.content:
                # raw 블록 저장 (assistant 메시지 재구성을 위해)
                assistant_response_content.append(block.to_dict()) 
                
                if block.type == "text":
                    text_in_response += block.text
                    has_text = True
                elif block.type == "tool_use":
                    tool_calls_in_response.append(block)
            
            # 어시스턴트의 응답을 메시지 기록에 추가
            if assistant_response_content:
                messages.append({"role": "assistant", "content": assistant_response_content})

            # 텍스트 응답이 있으면 메시지 업데이트 및 저장
            if has_text:
                latest_text_response = text_in_response
                await update_discord_message(reply_message, latest_text_response, force=True)

            # 도구 호출이 없으면 루프 종료
            if not tool_calls_in_response:
                logger.log("도구 호출 없음, 루프 종료.", logger.INFO)
                break

            # 도구 실행 및 결과 추가
            logger.log(f"{len(tool_calls_in_response)}개 도구 호출 감지됨. 실행 시작.", logger.INFO)
            tool_results_for_next_call = []
            for tool_call in tool_calls_in_response:
                # 도구 실행 알림 업데이트
                await update_discord_message(
                    reply_message,
                    f"{latest_text_response}\n\n`{tool_call.name}` 도구를 호출하는 중...",
                    force=True
                )
                
                # 도구 실행
                tool_result = await execute_tool(tool_call.name, tool_call.input, message.id)

                # 이미지 생성 또는 에러 처리
                if tool_result["type"] == "image_generation":
                    await image_generate(tool_result["prompt"], tool_result["size"], reply_message)
                    # 이미지 생성 완료 메시지를 결과로 추가 (return 제거)
                    result_content_str = f"이미지 생성 완료: 프롬프트 '{tool_result['prompt']}'"
                    tool_results_for_next_call.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": result_content_str
                    })
                    # 디스코드 메시지 업데이트
                    await update_discord_message(
                         reply_message,
                         f"{latest_text_response}\n\n`{tool_call.name}` 도구 실행 완료 (이미지 생성됨).",
                         force=True
                    )
                elif tool_result["type"] == "error":
                    error_message = f"{latest_text_response}\n\n도구 실행 오류 ({tool_call.name}): {tool_result['message']}"
                    await update_discord_message(reply_message, error_message, force=True)
                    return # 오류 발생 시 대화 종료
                elif tool_result["type"] == "tool_result":
                    # 성공적인 도구 결과 처리 (tool_result 타입 명시적 확인)
                    result_content_str = "\n".join([item.text for item in tool_result["result"] if hasattr(item, 'text')])
                    if not result_content_str.strip():
                        result_content_str = f"{tool_call.name} 도구 실행 완료, 결과 없음"
                    
                    # 다음 API 호출을 위해 결과 저장
                    tool_results_for_next_call.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": result_content_str
                    })

                    # 도구 실행 완료 알림 (선택적)
                    await update_discord_message(
                         reply_message,
                         f"{latest_text_response}\n\n`{tool_call.name}` 도구 실행 완료.",
                         force=True
                    )
            
            # 실행된 모든 도구 결과를 user 역할 메시지로 추가
            if tool_results_for_next_call:
                messages.append({"role": "user", "content": tool_results_for_next_call})
                logger.log("도구 결과 메시지 추가 완료.", logger.INFO)
            
            # 최대 라운드 도달 시 경고 및 종료 준비
            if current_round == max_tool_rounds:
                logger.log("최대 도구 호출 라운드 도달.", logger.WARNING)
                await update_discord_message(
                    reply_message,
                    f"{latest_text_response}\n\n[최대 도구 호출 횟수({max_tool_rounds})에 도달했습니다.]",
                    force=True
                )
                break # 루프 종료

        # 루프 종료 후 최종 상태 확인
        if not latest_text_response and not messages[-1]["role"] == "assistant":
             # 초기 응답도 없고, 마지막 메시지가 어시스턴트 응답도 아닌 경우 (예: 오류 없이 도구만 호출하다 끝난 경우)
             await update_discord_message(reply_message, "도구 실행은 완료되었지만 최종 응답이 없습니다.", force=True)

    except Exception as e:
        logger.log(f"Claude 응답 처리 오류: {str(e)}", logger.ERROR)
        traceback.print_exc()
        # reply_message가 초기화되었는지 확인 후 edit 호출
        if 'reply_message' in locals() and reply_message:
            await reply_message.edit(content=f"오류가 발생했습니다: {str(e)}")
        else:
            # reply_message가 없는 경우, 원본 메시지에 답글로 오류 메시지 전송 시도
            try:
                await message.reply(f"오류가 발생했습니다: {str(e)}")
            except Exception as fallback_e:
                logger.log(f"최종 오류 메시지 전송 실패: {fallback_e}", logger.CRITICAL) 