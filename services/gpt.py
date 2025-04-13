from openai import OpenAI
import discord

import traceback
import json
import datetime
import re
from core.logger import logger
from core.config import env
from services.prompts import system_prompts
from services.func import prompt_to_chat, create_image_embed
from services.mcp import get_gpt_functions
from services.web import search_and_crawl

# gpt_functions 가져오기
gpt_functions = get_gpt_functions()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=env.OPENAI_API_KEY)

async def image_generate(prompt: str, size: int, reply_message: discord.Message):
    sizestr = ["1024x1024", "1792x1024", "1024x1792"][size]

    try:
        response = client.images.generate(
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

# 사용 가능한 함수 등록
available_functions = {
    "search_and_crawl": search_and_crawl,
    "image_generate": image_generate,
}

async def chat(message, username, prompt, img_mode, img_url, second_response=False, second_function_name="", second_function_result="", message_object=None):
    # 이미지 모드인 경우 처리
    if img_mode:
        conversation = []
        conversation.append({"role": "user", "content": [{"type": "text", "text": f"{username}: {prompt}"}, {"type": "image_url", "image_url": {"url": img_url, "detail": "high"}}]})
    else:
        conversation = await prompt_to_chat(message, username, prompt)

    # 함수 호출 결과가 있는 경우
    if second_response:
        conversation.append({"role": "system", "content": f"당신은 이미 {second_function_name} 함수를 호출했고 아래는 실행결과입니다. 이 내용을 참고하여 답변하세요.\n{second_function_result}"})

    # GPT API 호출
    # 기본 시스템 프롬프트 가져오기
    base_prompts = system_prompts.copy() 
    # 첫 번째 시스템 프롬프트에 날짜 정보 추가
    if base_prompts and base_prompts[0]["role"] == "system":
        base_prompts[0]["content"] += f"\nToday is {datetime.datetime.now().strftime('%Y-%m-%d')} A.D."
        
    response = client.chat.completions.create(
        model=env.OPENAI_MODEL,
        messages=[
            # 기본 시스템 프롬프트 사용
            *base_prompts,
            *conversation
        ],
        frequency_penalty=0,
        presence_penalty=0,
        temperature=0.6,
        stream=True,
        tools=gpt_functions,
        tool_choice="auto"
    )
    
    # 응답 처리
    answer = ""
    reply_message = []
    
    if not message_object:
        reply_message.append(await message.reply(". . ."))
    else:
        reply_message.append(message_object)

    over_depth = 0
    over_num = 1900
    output_interval = 40
    finished = False
    function_name = ""
    function_args = ""
    function_call = False
    num = 0
    
    for chunk in response:
        finish_reason = chunk.choices[0].finish_reason
        tool_calls = chunk.choices[0].delta.tool_calls
        
        if finish_reason == "tool_calls":
            break
        elif tool_calls is not None:
            function_call = True
            tool_call = chunk.choices[0].delta.tool_calls[0]
            if tool_call.function.name is not None:
                function_name += tool_call.function.name
            if tool_call.function.arguments is not None:
                function_args += tool_call.function.arguments
        else:
            chunk_message = chunk.choices[0].delta.content
            if chunk_message is not None:
                answer += chunk_message
            else:
                finished = True
                
            # 응답이 너무 길면 여러 메시지로 분할
            if len(answer) >= over_num:
                reply_message.append(await message.reply(". . ."))
                over_depth += 1
                answer = answer.replace("```", "\n```")
                
                # 코드 블록이 끝나지 않은 경우 처리
                if answer.count("```") % 2 == 1:
                    await reply_message[over_depth].edit(content=answer + "\n```")
                    pattern = re.compile(r"```[a-zA-Z]*")
                    answer = pattern.findall(answer)[-1] + "\n"
                else:
                    await reply_message[over_depth].edit(content=answer)
                    answer = ""
            # 정기적으로 메시지 업데이트
            elif num % output_interval == 0 and not (answer == "" or answer == "\n" or answer == "\n\n"):
                await reply_message[over_depth].edit(content=answer)
            num += 1
            
    # 함수 호출 또는 응답 처리
    if function_call:
        logger.log(f"GPT Function call: {function_name} {function_args}", logger.INFO)
        await gpt_function_call(function_name, function_args, reply_message[over_depth], message, username, prompt)
    elif finished:
        await reply_message[over_depth].edit(content=answer)


async def gpt_function_call(function_name, function_args, reply_message, message, username, prompt):
    if function_name in available_functions:
        if function_name == "search_and_crawl":
            args = json.loads(function_args)
            await reply_message.edit(content=f"{args['keyword']} 검색중...")
            function_result = await available_functions[function_name](args['keyword'])
            if function_result is None:
                function_result = "검색 결과를 찾을 수 없습니다."
            await chat(message, username, prompt, False, "", True, function_name, function_result, reply_message)
        elif function_name == "image_generate":
            args = json.loads(function_args)
            await reply_message.edit(content=f"{args['prompt']} 이미지 생성중...")
            await available_functions[function_name](args['prompt'], args['size'], reply_message) 