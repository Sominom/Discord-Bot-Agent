import json
from typing import Optional, Tuple, List, Dict, Any
from openai import AsyncOpenAI
from core.config import env
from core.logger import logger

class AIService:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIService, cls).__new__(cls)
        return cls._instance

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            try:
                self._client = AsyncOpenAI(api_key=env.OPENAI_API_KEY)
                logger.log("OpenAI 비동기 클라이언트 초기화 완료")
            except Exception as e:
                logger.log(f"OpenAI 클라이언트 초기화 실패: {str(e)}", logger.ERROR)
                raise
        return self._client

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Any:
        try:
            prompt_for_api = prompt if len(prompt) <= 1000 else f"{prompt[:997]}..."
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt_for_api,
                n=1,
                size=size,
            )
            return response.data
        except Exception as e:
            logger.log(f"이미지 생성 실패: {str(e)}", logger.ERROR)
            raise

    async def is_message_for_bot(self, message_content: str, username: str, bot_name: str, recent_messages: List[dict] = None) -> Tuple[bool, float]:
        try:
            context = ""
            if recent_messages:
                for msg in recent_messages:
                    author = "봇" if msg["is_bot"] else msg["author"]
                    context += f"{author}: {msg['content']}\n"
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"당신은 메시지가 봇에게 보내는 것인지 판단하는 AI입니다. 최근 대화 맥락과 메시지 내용을 분석하여 메시지가 '{bot_name}'에게 보내는 것인지 판단하세요."},
                    {"role": "user", "content": f"최근 대화 맥락:\n{context}\n\n사용자 '{username}'의 새 메시지: {message_content}\n\n이 메시지가 봇('{bot_name}')에게 보내는 것인지 판단하세요. JSON 형식으로 다음을 반환하세요: {{\"is_for_bot\": true/false, \"confidence\": 0~1, \"reason\": \"판단 이유\"}}"}
                ],
            )
            
            result_text = response.choices[0].message.content
            try:
                result = json.loads(result_text)
                return result.get("is_for_bot", False), result.get("confidence", 0)
            except json.JSONDecodeError:
                logger.log(f"JSON 파싱 오류: {result_text}", logger.ERROR)
                return False, 0
        except Exception as e:
            logger.log(f"메시지 판단 오류: {str(e)}", logger.ERROR)
            return False, 0

    def get_max_response_tokens(self) -> int:
        return getattr(env, "MAX_RESPONSE_TOKENS", 2000)

ai_service = AIService()
