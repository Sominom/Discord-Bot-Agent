import logging
from typing import Dict, Any, List, Tuple

from openai import OpenAI
from core.config import env
from core.logger import logger
import json

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=env.OPENAI_API_KEY)


async def is_message_for_bot(message_content: str, username: str, bot_name: str, recent_messages: List[dict] = None) -> Tuple[bool, float]:
    try:
        # 메시지 컨텍스트 구성
        context = ""
        if recent_messages:
            for msg in recent_messages:
                author = "봇" if msg["is_bot"] else msg["author"]
                context += f"{author}: {msg['content']}\n"
        
        # OpenAI API 요청
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": f"당신은 메시지가 봇에게 보내는 것인지 판단하는 AI입니다. 최근 대화 맥락과 메시지 내용을 분석하여 메시지가 '{bot_name}'에게 보내는 것인지 판단하세요."},
                {"role": "user", "content": f"최근 대화 맥락:\n{context}\n\n사용자 '{username}'의 새 메시지: {message_content}\n\n이 메시지가 봇('{bot_name}')에게 보내는 것인지 판단하세요. JSON 형식으로 다음을 반환하세요: {{\"is_for_bot\": true/false, \"confidence\": 0~1, \"reason\": \"판단 이유\"}}"}
            ],
            temperature=0
        )
        
        # 응답 추출
        result_text = response.choices[0].message.content
        try:
            result = json.loads(result_text)
            is_for_bot = result.get("is_for_bot", False)
            confidence = result.get("confidence", 0)
            return is_for_bot, confidence
        except json.JSONDecodeError:
            logger.error(f"JSON 파싱 오류: {result_text}")
            return False, 0
    except Exception as e:
        logger.error(f"메시지 판단 오류: {str(e)}")
        return False, 0

async def is_conversation_ending(message_content):
    
    try:
        # 간단한 키워드 매칭으로 대화 종료 여부 판단
        ending_keywords = [
            "알겠어", "알겠습니다", "알았어", "알았습니다", "고마워", "감사합니다", "감사해요",
            "ㄱㅅ", "ㄱㅅㅇ", "ㄱㅅㅎㄴㄷ", "땡큐", "ㅌㅋ", "OK", "오케이", "ㅇㅋ", "ㅇㅋㅇㅋ",
            "멋있다", "잘했어", "수고해", "수고했어", "그래", "그렇구나", "응", "넵", "네"
        ]
        
        # GPT를 사용한 더 정확한 판단
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "당신은 메시지가 대화를 종료하는 내용인지 판단하는 AI입니다. '알겠어', '고마워', '수고해' 등의 대화를 마무리하는 표현을 감지하세요."},
                {"role": "user", "content": f"메시지: \"{message_content}\"\n\n이 메시지가 대화를 종료하는 표현인지 판단하세요. JSON 형식으로 다음을 반환하세요: {{\"is_ending\": true/false, \"reason\": \"판단 이유\", \"suggested_emoji\": \"적절한 이모지\"}}"}
            ],
            temperature=0
        )
        
        result_text = response.choices[0].message.content
        try:
            result = json.loads(result_text)
            is_ending = result.get("is_ending", False)
            suggested_emoji = result.get("suggested_emoji", "👍")
            return is_ending, suggested_emoji
        except json.JSONDecodeError:
            logger.error(f"JSON 파싱 오류: {result_text}")
            # 간단한 키워드 매칭으로 폴백
            for keyword in ending_keywords:
                if keyword in message_content.lower():
                    return True, "👍"
            return False, None
    except Exception as e:
        logger.error(f"대화 종료 판단 오류: {str(e)}")
        return False, None 