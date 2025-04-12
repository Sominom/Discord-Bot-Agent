import logging
from typing import Dict, Any, List, Tuple

from openai import OpenAI
from core.config import env
from core.logger import logger

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=env.OPENAI_API_KEY)

async def is_message_for_bot(message_content: str, username: str, bot_name: str, recent_messages: List[dict] = None) -> Tuple[bool, float]:
    """
    OpenAI를 사용하여 메시지가 봇에게 보내는 것인지 판단
    
    Args:
        message_content: 사용자 메시지 내용
        username: 메시지 작성자 이름
        bot_name: 봇 이름
        recent_messages: 최근 대화 내용 목록 (최대 5개)
    
    Returns:
        Tuple[bool, float]: (봇에게 보내는 메시지인지 여부, 확률)
    """
    try:
        # 시스템 프롬프트 준비
        system_prompt = f"""당신은 메시지가 봇에게 보내는 것인지 아닌지 판단하는 분류기입니다.
        메시지가 다음과 같은 특성을 가지면 봇에게 보내는 것으로 판단하세요:
        1. 봇 이름({bot_name})을 직접 언급
        2. 질문이나 명령의 형태
        3. 봇에게 응답을 요청하는 내용
        4. 다른 특정 사용자를 언급하지 않음
        5. 봇이 이전에 한 말에 대한 응답
        6. 이전 대화 맥락상 봇과의 대화 지속으로 보이는 경우

        판단 결과를 JSON 형식으로 반환하세요: {{"is_for_bot": true/false, "confidence": 0.0~1.0}}
        """

        # 메시지 준비
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 최근 대화 내용 추가
        if recent_messages and len(recent_messages) > 0:
            messages.append({"role": "user", "content": "다음은 최근 대화 내용입니다:"})
            
            conversation_context = ""
            for msg in recent_messages:
                sender_name = bot_name if msg["is_bot"] else msg["author"]
                conversation_context += f"{sender_name}: {msg['content']}\n"
            
            messages.append({"role": "assistant", "content": conversation_context})
        
        # 현재 메시지 추가
        messages.append({"role": "user", "content": f"사용자({username}): {message_content}"})
        
        # API 호출
        response = openai_client.chat.completions.create(
            model=env.OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0.1
        )
        
        # 응답 파싱
        try:
            import json
            result = json.loads(response.choices[0].message.content)
            is_for_bot = result.get("is_for_bot", False)
            confidence = result.get("confidence", 0.0)
            
            logger.log(f"메시지 분류 결과: 봇 대상={is_for_bot}, 확률={confidence}", logger.INFO)
            return is_for_bot, confidence
            
        except Exception as e:
            logger.log(f"응답 파싱 오류: {str(e)}", logger.ERROR)
            return False, 0.0
            
    except Exception as e:
        logger.log(f"메시지 분류 오류: {str(e)}", logger.ERROR)
        return False, 0.0 