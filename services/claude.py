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
    """DALL-E를 사용하여 이미지를 생성합니다"""
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

async def get_claude_response(messages: List[Dict[str, Any]], tools=None, stream=True) -> Any:
    """Claude API 호출 및 응답 처리"""
    try:
        # 시스템 프롬프트 추출
        system_prompt = None
        filtered_messages = []
        
        # 시스템 메시지가 있으면 시스템 프롬프트로 추가
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append(msg)
        
        # 스트리밍이 아닌 경우
        if not stream:
            if tools:
                response = claude_client.messages.create(
                    model=env.CLAUDE_MODEL,
                    system=system_prompt,
                    messages=filtered_messages,
                    temperature=0.7,
                    max_tokens=2000,
                    tools=tools,
                    stream=False
                )
            else:
                response = claude_client.messages.create(
                    model=env.CLAUDE_MODEL,
                    system=system_prompt,
                    messages=filtered_messages,
                    temperature=0.7,
                    max_tokens=2000,
                    stream=False
                )
            return response
        
        # 스트리밍 모드
        if tools:
            response_stream = claude_client.messages.create(
                model=env.CLAUDE_MODEL,
                system=system_prompt,
                messages=filtered_messages,
                temperature=0.7,
                max_tokens=2000,
                tools=tools,
                stream=True
            )
        else:
            response_stream = claude_client.messages.create(
                model=env.CLAUDE_MODEL,
                system=system_prompt,
                messages=filtered_messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )
        
        return response_stream
            
    except Exception as e:
        logger.log(f"Claude API 호출 오류: {str(e)}", logger.ERROR)
        traceback.print_exc()
        return {"error": str(e)}

async def extract_tool_info(message_chunks, tool_name=None):
    """청크에서 도구 정보를 추출하는 간소화된 함수"""
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
    """도구를 실행하고 결과를 반환하는 함수"""
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
    """디스코드 메시지 업데이트 함수"""
    if len(current_text) - last_update_length >= 40 or force:
        last_update_length = len(current_text)
        
        # 메시지 길이가 1900자를 초과하면 자르기
        if len(current_text) > 1900:
            current_text = current_text[:1900] + "..."
        
        await message.edit(content=current_text)
        return last_update_length
    
    return last_update_length

async def process_tool_result(tool_result_content, server_id=None):
    """도구 결과에서 서버 ID 추출 및 다음 도구에 필요한 정보 처리"""
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
    """대화에 도구 사용 및 결과를 추가하는 함수"""
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
        conversation = []
        conversation.append({"role": "user", "content": [
            {"type": "text", "text": f"{username}: {prompt}"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_url}}
        ]})
    else:
        # 대화 기록 가져오기
        conversation = await prompt_to_chat(message, username, prompt)

    # 기본 시스템 프롬프트 가져오기
    base_prompts = system_prompts.copy()
    
    # 첫 번째 시스템 프롬프트에 날짜 정보 추가
    if base_prompts and base_prompts[0]["role"] == "system":
        base_prompts[0]["content"] += f"\nToday is {datetime.datetime.now().strftime('%Y-%m-%d')} A.D."
        # 서버 이름과 채널 이름 추가
        server_name = message.guild.name if message.guild else "DM"
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "Direct Message"
        base_prompts[0]["content"] += f"\n현재 서버: {server_name}, 채널: {channel_name}"
        # 메시지 ID 추가
        base_prompts[0]["content"] += f"\ncurrent_message_id: {message.id}"
    
    # MCP 도구 정의
    mcp_tools = get_mcp_tools()
    
    # 메시지 준비 및 응답 처리
    messages = [
        *base_prompts,
        *conversation
    ]
    
    # 메시지 객체가 없는 경우 새로 생성
    if not message_object:
        reply_message = await message.reply(". . .")
    else:
        reply_message = message_object
        
    try:
        # 변수 초기화
        current_text = ""
        message_chunks = []
        last_update_length = 0
        tool_calls_queue = []
        extracted_server_id = None  # 서버 ID 추출 변수 추가
        
        # 스트리밍 모드 응답 요청
        response_stream = await get_claude_response(messages, mcp_tools, stream=True)
        
        # 스트림 처리
        tool_use_detected = False
        current_content_block = None
        current_tool_use_id = None
        
        with response_stream as stream:
            for chunk in stream:
                # 모든 청크 저장
                message_chunks.append(chunk)
                
                # 콘텐츠 블록 시작 이벤트
                if hasattr(chunk, 'type') and chunk.type == 'content_block_start':
                    if hasattr(chunk, 'content_block'):
                        # 도구 사용 블록인지 확인
                        if hasattr(chunk.content_block, 'type') and chunk.content_block.type == 'tool_use':
                            tool_use_detected = True
                            current_content_block = chunk.content_block
                            if hasattr(current_content_block, 'id'):
                                current_tool_use_id = current_content_block.id
                            last_update_length = await update_discord_message(reply_message, "도구를 호출하는 중...", force=True)
                
                # 청크에 델타가 있는 경우 처리
                if hasattr(chunk, 'delta') and chunk.delta:
                    # 텍스트 델타
                    if hasattr(chunk.delta, 'type') and chunk.delta.type == 'text_delta':
                        if hasattr(chunk.delta, 'text'):
                            current_text += chunk.delta.text
                            # 주기적 메시지 업데이트
                            last_update_length = await update_discord_message(reply_message, current_text, last_update_length=last_update_length)
                    
                    # 도구 사용 델타
                    elif hasattr(chunk.delta, 'tool_use'):
                        # 도구 사용 정보 업데이트
                        if not tool_use_detected:
                            tool_use_detected = True
                            current_content_block = chunk.delta.tool_use
                            last_update_length = await update_discord_message(reply_message, "도구를 호출하는 중...", force=True)
                        else:
                            # 도구 이름 업데이트
                            if hasattr(chunk.delta.tool_use, 'name'):
                                if not hasattr(current_content_block, 'name') or not current_content_block.name:
                                    current_content_block.name = ""
                                current_content_block.name = chunk.delta.tool_use.name
                                last_update_length = await update_discord_message(reply_message, f"{current_content_block.name} 도구를 호출하는 중...", force=True)
                            
                            # 도구 ID 업데이트
                            if hasattr(chunk.delta.tool_use, 'id'):
                                current_content_block.id = chunk.delta.tool_use.id
                                current_tool_use_id = chunk.delta.tool_use.id
                
                # 콘텐츠 블록 완료 이벤트
                if hasattr(chunk, 'type') and chunk.type == 'content_block_stop':
                    # 현재 블록이 도구 사용 블록인 경우 실행
                    if tool_use_detected and current_content_block and hasattr(current_content_block, 'name'):
                        # 누적된 청크에서 도구 정보 추출
                        tool_info, extracted_text = await extract_tool_info(message_chunks, current_content_block.name)
                        
                        # 추출한 정보로 current_content_block 업데이트
                        if not tool_info["id"] and hasattr(current_content_block, 'id'):
                            tool_info["id"] = current_content_block.id
                        elif not hasattr(current_content_block, 'id') or not current_content_block.id:
                            current_content_block.id = tool_info["id"]
                        
                        # 서버 ID 자동 전달 (이전 도구 호출에서 얻은 경우)
                        if extracted_server_id and tool_info["name"] != "get_server_id_from_message" and "server_id" in str(tool_info["input"]) and not tool_info["input"].get("server_id"):
                            logger.log(f"이전에 추출한 서버 ID를 도구 입력에 자동 전달: {extracted_server_id}", logger.INFO)
                            tool_info["input"]["server_id"] = extracted_server_id
                        
                        # 도구 실행
                        last_update_length = await update_discord_message(reply_message, f"{tool_info['name']} 도구를 실행 중...", force=True)
                        
                        # 도구 실행 및 결과 처리
                        execution_result = await execute_tool(tool_info["name"], tool_info["input"], message.id)
                        
                        # 결과 타입에 따른 처리
                        if execution_result["type"] == "image_generation":
                            # 이미지 생성은 별도 처리
                            await image_generate(execution_result["prompt"], execution_result["size"], reply_message)
                            return
                        elif execution_result["type"] == "error":
                            # 에러 처리
                            last_update_length = await update_discord_message(reply_message, f"도구 실행 오류: {execution_result['message']}", force=True)
                            return
                        else:
                            # 도구 실행 결과 처리
                            result = execution_result["result"]
                            result_content = "\n".join([item.text for item in result if hasattr(item, 'text')])
                            
                            # 결과가 비어있는 경우 기본 텍스트 사용
                            if not result_content.strip():
                                result_content = f"{tool_info['name']} 도구 실행 완료, 결과 없음"
                            
                            # 서버 ID 추출 확인 (get_server_id_from_message 도구인 경우)
                            if tool_info["name"] == "get_server_id_from_message":
                                # 결과에서 서버 ID 추출
                                server_match = re.search(r"서버 ID:\s*(\d+)", result_content)
                                if server_match:
                                    extracted_server_id = server_match.group(1)
                                    logger.log(f"서버 ID 추출 성공: {extracted_server_id}", logger.INFO)
                            
                            # 도구 결과를 포함하여 새 메시지 구성
                            new_messages, extracted_id = await process_tool_in_conversation(messages, tool_info, result_content)
                            
                            # 추출된 서버 ID 업데이트
                            if extracted_id and not extracted_server_id:
                                extracted_server_id = extracted_id
                                logger.log(f"process_tool_in_conversation에서 서버 ID 업데이트: {extracted_server_id}", logger.INFO)
                            
                            # 후속 응답 요청
                            last_update_length = await update_discord_message(reply_message, f"{tool_info['name']} 도구 실행 결과를 처리 중...", force=True)
                            
                            # 비스트리밍 모드로 후속 응답 요청
                            follow_up_response = await get_claude_response(new_messages, mcp_tools, stream=False)
                            
                            # 중요: 여기서 새 메시지와 도구 정보 큐에 저장
                            tool_calls_queue.append({
                                "messages": new_messages,
                                "response": follow_up_response,
                                "server_id": extracted_server_id  # 서버 ID 전달
                            })
                        
                        # 도구 처리 후 상태 초기화
                        tool_use_detected = False
                        current_content_block = None
                        current_tool_use_id = None
                
                # 메시지 완료 이벤트
                if hasattr(chunk, 'type') and chunk.type == 'message_stop':
                    # 마지막 업데이트
                    last_update_length = await update_discord_message(reply_message, current_text, force=True)
                    break
        
        # 연속적인 도구 호출 처리
        if tool_calls_queue:
            for tool_call in tool_calls_queue:
                follow_up_response = tool_call["response"]
                new_messages = tool_call["messages"]
                current_server_id = tool_call.get("server_id")  # 서버 ID 전달
                
                if hasattr(follow_up_response, 'content') and follow_up_response.content:
                    # 텍스트와 도구 사용 블록 분리
                    text_blocks = []
                    tool_use_blocks = []
                    
                    for block in follow_up_response.content:
                        if block.type == "text":
                            text_blocks.append(block.text)
                        elif block.type == "tool_use":
                            tool_use_blocks.append(block)
                    
                    # 텍스트 응답 업데이트
                    if text_blocks:
                        current_text = "\n".join(text_blocks)
                        last_update_length = await update_discord_message(reply_message, current_text, force=True)
                    
                    # 추가 도구 호출이 있는 경우 처리
                    for tool_block in tool_use_blocks:
                        next_tool_info = {
                            "id": tool_block.id if hasattr(tool_block, 'id') else None,
                            "name": tool_block.name if hasattr(tool_block, 'name') else None,
                            "input": tool_block.input if hasattr(tool_block, 'input') else {}
                        }
                        
                        # 서버 ID 자동 추가 (이전에 추출된 경우)
                        if current_server_id and "server_id" in str(next_tool_info["input"]) and not next_tool_info["input"].get("server_id"):
                            logger.log(f"연속 도구 호출에 서버 ID 자동 추가: {current_server_id}", logger.INFO)
                            next_tool_info["input"]["server_id"] = current_server_id
                        
                        # 도구 실행 알림
                        last_update_length = await update_discord_message(
                            reply_message, 
                            f"{current_text}\n\n{next_tool_info['name']} 도구를 추가로 호출하는 중...", 
                            force=True
                        )
                        
                        # get_server_id_from_message 특화 처리
                        if next_tool_info["name"] == "get_server_id_from_message" and "message_id" not in next_tool_info["input"]:
                            next_tool_info["input"]["message_id"] = str(message.id)
                        
                        # 추가 도구 실행
                        execution_result = await execute_tool(next_tool_info["name"], next_tool_info["input"], message.id)
                        
                        # 결과 타입에 따른 처리
                        if execution_result["type"] == "image_generation":
                            # 이미지 생성은 별도 처리
                            await image_generate(execution_result["prompt"], execution_result["size"], reply_message)
                            return
                        elif execution_result["type"] == "error":
                            # 에러 처리
                            last_update_length = await update_discord_message(
                                reply_message,
                                f"{current_text}\n\n추가 도구 실행 오류: {execution_result['message']}", 
                                force=True
                            )
                            return
                        else:
                            # 도구 실행 결과 처리
                            result = execution_result["result"]
                            result_content = "\n".join([item.text for item in result if hasattr(item, 'text')])
                            
                            # 결과가 비어있는 경우 기본 텍스트 사용
                            if not result_content.strip():
                                result_content = f"{next_tool_info['name']} 도구 실행 완료, 결과 없음"
                            
                            # 서버 ID 업데이트 (get_server_id_from_message인 경우)
                            if next_tool_info["name"] == "get_server_id_from_message":
                                server_match = re.search(r"서버 ID:\s*(\d+)", result_content)
                                if server_match:
                                    current_server_id = server_match.group(1)
                                    logger.log(f"연속 도구 호출에서 서버 ID 추출: {current_server_id}", logger.INFO)
                            
                            # 도구 결과를 포함하여 새 메시지 구성
                            final_messages, extracted_id = await process_tool_in_conversation(new_messages, next_tool_info, result_content)
                            
                            # 추출된 서버 ID 업데이트
                            if extracted_id and not current_server_id:
                                current_server_id = extracted_id
                                logger.log(f"연속 도구: process_tool_in_conversation에서 서버 ID 업데이트: {current_server_id}", logger.INFO)
                            
                            # 최종 응답 요청
                            last_update_length = await update_discord_message(
                                reply_message,
                                f"{current_text}\n\n{next_tool_info['name']} 도구 결과를 처리 중...", 
                                force=True
                            )
                            
                            # 최종 응답 요청
                            final_response = await get_claude_response(final_messages, stream=False)
                            
                            # 최종 응답 처리
                            if hasattr(final_response, 'content') and final_response.content:
                                final_text = ""
                                has_more_tools = False
                                
                                for final_block in final_response.content:
                                    if final_block.type == "text":
                                        final_text += final_block.text
                                    elif final_block.type == "tool_use":
                                        has_more_tools = True
                                        logger.log(f"추가 도구 호출 감지됨: {final_block.name}", logger.WARNING)
                                
                                # 최종 응답 업데이트
                                if final_text:
                                    if has_more_tools:
                                        final_text += "\n\n[알림: 더 이상의 도구 호출은 처리되지 않습니다. 필요하다면 새로운 메시지를 보내세요.]"
                                    last_update_length = await update_discord_message(reply_message, final_text, force=True)
    except Exception as e:
        logger.log(f"Claude 응답 처리 오류: {str(e)}", logger.ERROR)
        traceback.print_exc()
        await reply_message.edit(content=f"오류가 발생했습니다: {str(e)}")

def get_mcp_tools():
    """MCP 도구 정의"""
    return [
        {
            "name": "search_and_crawl",
            "description": "구글 검색 후 크롤링한 결과를 반환합니다",
            "input_schema": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색할 키워드"
                    }
                },
                "required": ["keyword"]
            }
        },
        {
            "name": "get_server_id_from_message",
            "description": "현재 대화의 서버 ID를 자동으로 추출합니다. 별도의 파라미터가 필요하지 않습니다.",
            "input_schema": {
                "type": "object",
                "properties": {"message_id": {"type": "string", "description": "메시지 ID (선택 사항, 입력하지 않아도 현재 메시지 ID가 자동으로 사용됨)"}},
                "required": []
            }
        },
        {
            "name": "send_message",
            "description": "특정 채널에 메시지를 전송합니다.",
            "input_schema": {
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
        },
        {
            "name": "read_messages",
            "description": "채널에서 최근 메시지를 읽습니다.",
            "input_schema": {
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
        },
        {
            "name": "get_user_info",
            "description": "디스코드 사용자 정보를 조회합니다.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "디스코드 사용자 ID"
                    }
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "get_server_info",
            "description": "디스코드 서버 정보를 조회합니다.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "디스코드 서버(길드) ID"
                    }
                },
                "required": ["server_id"]
            }
        },
        {
            "name": "list_members",
            "description": "서버 멤버 목록을 조회합니다.",
            "input_schema": {
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
        },
        {
            "name": "add_role",
            "description": "사용자에게 역할을 추가합니다.",
            "input_schema": {
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
        },
        {
            "name": "remove_role",
            "description": "사용자에게서 역할을 제거합니다.",
            "input_schema": {
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
        },
        {
            "name": "create_text_channel",
            "description": "새 텍스트 채널을 생성합니다.",
            "input_schema": {
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
        },
        {
            "name": "delete_channel",
            "description": "채널을 삭제합니다.",
            "input_schema": {
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
        },
        {
            "name": "add_reaction",
            "description": "메시지에 반응을 추가합니다.",
            "input_schema": {
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
        },
        {
            "name": "add_multiple_reactions",
            "description": "메시지에 여러 반응을 추가합니다.",
            "input_schema": {
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
        },
        {
            "name": "remove_reaction",
            "description": "메시지에서 반응을 제거합니다.",
            "input_schema": {
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
        },
        {
            "name": "moderate_message",
            "description": "메시지를 삭제하고 선택적으로 사용자 타임아웃 처리합니다.",
            "input_schema": {
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
                        "maximum": 40320
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        },
        {
            "name": "generate_image",
            "description": "DALL-E를 사용하여 이미지를 생성합니다.",
            "input_schema": {
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
        }
    ] 