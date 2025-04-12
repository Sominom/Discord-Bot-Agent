from openai import OpenAI

import traceback
import json
import datetime
import re
from data.config import Config
from data.bot_logger import BotLogger
from data.prompts import system_prompts
from utils.func import prompt_to_chat, create_image_embed
from utils.tools import gpt_functions
ts = Translate()
config = Config()
Logger = BotLogger()
client = OpenAI(api_key=config.openai_api_key)
from utils.web import search_and_crawl


async def image_generate(prompt: str, size: int, ctx=None):
    sizestr = ["1024x1024", "1792x1024", "1024x1792"][size]

    try:
        response = client.images.generate(model="dall-e-3",
        prompt=prompt,
        n=1,
        size=sizestr)
        data: list = response.data
        for index, image in enumerate(data):
            title = f"{prompt}"
            embed = create_image_embed(title, prompt, image.url)
        await ctx.edit(content=f"이미지를 생성했습니다. {prompt}", embed=embed)
    except Exception as err:
        traceback.print_exc()
        await ctx.edit(content=f"이미지를 생성하는데 오류가 발생했습니다. {str(err)}")

available_functions = {
    "search_and_crawl": search_and_crawl,
    "image_generate": image_generate,
}

async def chat(ctx, username, prompt, img_mode, img_url, second_response=False, second_function_name="", second_function_result="", message_object=None):
    if img_mode:
        conversation = []
        conversation.append({"role": "user", "content": [{"type": "text", "text": f"{username}: {prompt}"}, {"type": "image_url", "image_url": {"url": img_url, "detail": "high"}}]})
    else:
        conversation = await prompt_to_chat(ctx, username, prompt)

    if second_response:
        conversation.append({"role": "system", "content": f"당신은 이미 {second_function_name} 함수를 호출했고 아래는 실행결과입니다. 이 내용을 참고하여 답변하세요.\n{second_function_result}"})

    response = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": f"Today: {datetime.datetime.now().strftime('%Y-%m-%d')}"},
            
            *conversation
        ],
        frequency_penalty=0,
        presence_penalty=0,
        temperature=0.6,
        stream=True,
        tools=gpt_functions,
        tool_choice="auto"
    )
    answer = ""

    reply_message = []
    if not message_object:
        reply_message.append(await ctx.reply(ts.text('. . .')))
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
            if len(answer) >= over_num:
                reply_message.append(await ctx.reply(". . ."))
                over_depth += 1
                answer = answer.replace("```", "\n```")
                if answer.count("```") % 2 == 1:
                    reply_message[over_depth].edit(content=answer+ "\n```")
                    pattern = re.compile(r"```[a-zA-Z]*")
                    answer = pattern.findall(answer)[-1] + "\n"
                else:
                    await reply_message[over_depth].edit(content=answer)
                    answer = ""
            elif num % output_interval == 0 and not (answer == "" or answer == "\n" or answer == "\n\n"):
                await reply_message[over_depth].edit(content=answer)
            num += 1
    if function_call:
        Logger.log(f"{ts.text('GPT Function call:')} {function_name} {function_args}", Logger.INFO)
        await gpt_function_call(function_name, function_args, reply_message[over_depth], ctx, username, prompt)
    elif finished:
        await reply_message[over_depth].edit(content=answer)


async def gpt_function_call(function_name, function_args, reply_message, ctx, username, prompt):
    if function_name in available_functions:
        if function_name == "search_and_crawl":
            args = json.loads(function_args)
            await reply_message.edit(content=f"{args['keyword']} 검색중...")
            function_result = await available_functions[function_name](args['keyword'])
            if function_result is None:
                function_result = "검색 결과를 찾을 수 없습니다."
            await chat(ctx, username, prompt, False, "", True, function_name, function_result, reply_message)
        elif function_name == "image_generate":
            args = json.loads(function_args)
            await reply_message.edit(content=f"{args['prompt']} 이미지 생성중...")
            await available_functions[function_name](args['prompt'], args['size'], reply_message)

