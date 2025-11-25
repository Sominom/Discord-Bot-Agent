
## 기능
- OpenAI GPT + MCP 기반 실시간 대화
- DALL-E를 통한 이미지 생성
- 디스코드 채널 관리 기능 (MCP 통합)
- 역할 관리, 메시지 관리 등 다양한 디스코드 관리 기능
- 메시지 분류: 봇에게 보내는 메시지인지 자동 판단 (OpenAI)

## 설치 및 실행

1. 의존성 설치
```bash
pip install -r requirements.txt
```

2. `config.json` 파일 설정

`config.json.sample` 파일을 `config.json`으로 복사하고 설정을 입력합니다.

```json
{
  "BOT_NAME": "괴상한 봇",
  "BOT_IDENTITY": "당신은 괴상한 개발자 모임인 괴상한 괴발자 디스코드 채널의 봇입니다. 당신은 괴상한 개발자 모임의 일원이며, 디스코드 서버를 관리하고, 개발자들을 돕습니다.",
  "BOT_START_MESSAGE": "앗! 안녕하세요! 저는 괴상한 봇입니다! 무엇이든 물어봐주세요! U3U~ <3",
  "DISCORD_BOT_KEY": "",
  "OPENAI_API_KEY": "",
  "OPENAI_MODEL": "gpt-4.1-mini",
  "GOOGLE_API_KEY": "",
  "CUSTOM_SEARCH_ENGINE_ID": "",
  "HISTORY_NUM": 5,
  "DISCORD_OWNER_IDS": ["your_discord_id1", "your_discord_id2"],
  "MAX_HISTORY_COUNT": 10,
  "MAX_RESPONSE_TOKENS": 2000,
  "VERTEX_API_KEY": ""
}
```

3. 봇 실행
```bash
python bot.py
```

## MCP(Model Context Protocol) 통합

디스코드 인터페이스와 OpenAI GPT 모델 간 상호작용을 위해 MCP(Model Context Protocol) 서버를 내장합니다.
이 프로젝트는 채팅을 통해 디스코드 서버 관리 기능을 자동화하며 이미지 생성, 검색 등의 기능도 제공합니다.

시스템 구성:
- MCP 서버는 Discord 애플리케이션과 동일한 프로세스에서 실행되며 stdio 기반으로 통신합니다.
- 채팅 입력 시 GPT-4.1 계열 모델이 메시지가 봇을 향한 것인지 판단합니다.
- 본 대화 엔진은 OpenAI Chat Completions + MCP 툴을 사용하여 사용자 의도를 분석하고 필요한 툴을 실행합니다.
- 디스코드 채팅 인터페이스는 MCP 툴 실행 결과를 사용자에게 실시간으로 전달합니다.

복잡한 디스코드 서버 관리 작업을 단순한 채팅 명령으로 수행할 수 있게 하여 관리 효율성을 크게 향상시킵니다.

## 사용 가능한 MCP 툴 목록

다음은 현재 봇에서 사용할 수 있는 MCP 툴 목록입니다:

**검색 및 생성:**
*   `search_and_crawl`: 구글 검색 후 크롤링한 결과를 반환합니다.
*   `generate_image`: DALL-E를 사용하여 이미지를 생성합니다.

**서버 정보:**
*   `get_server_info`: 디스코드 서버 정보를 조회합니다.
*   `list_members`: 서버 멤버 목록을 조회합니다.
*   `get_server_id_from_message`: 메시지에서 서버 ID를 자동으로 추출합니다.
*   `list_categories`: 서버의 카테고리 목록을 조회합니다.

**역할 관리:**
*   `add_role`: 사용자에게 역할을 추가합니다.
*   `remove_role`: 사용자에게서 역할을 제거합니다.
*   `create_role`: 서버에 새로운 역할을 생성합니다.
*   `delete_role`: 서버에서 역할을 삭제합니다.

**채널 관리:**
*   `create_text_channel`: 새 텍스트 채널을 생성합니다.
*   `create_voice_channel`: 새 음성 채널을 생성합니다.
*   `create_category`: 새 카테고리를 생성합니다.
*   `delete_category`: 카테고리를 삭제합니다.
*   `move_channel`: 채널을 다른 카테고리로 이동합니다.
*   `rename_channel`: 채널 이름을 변경합니다.
*   `set_slowmode`: 채널 슬로우 모드를 설정합니다.
*   `create_invite`: 서버 초대 링크를 생성합니다.
*   `disconnect_member`: 음성 채널에서 멤버 연결을 끊습니다.
*   `delete_channel`: 채널을 삭제합니다.
*   `search_channel`: 서버 내에서 채널 이름으로 채널을 검색합니다.
*   `get_channel_info`: 채널 ID로 채널의 상세 정보를 조회합니다.
*   `set_channel_topic`: 텍스트 채널의 주제(토픽)를 설정합니다.

**메시지 및 반응:**
*   `add_reaction`: 메시지에 반응을 추가합니다.
*   `add_multiple_reactions`: 메시지에 여러 반응을 추가합니다.
*   `remove_reaction`: 메시지에서 반응을 제거합니다.
*   `send_message`: 특정 채널에 메시지를 전송합니다.
*   `send_embed`: 지정된 채널에 임베드 메시지를 전송합니다.
*   `read_messages`: 채널에서 최근 메시지를 읽습니다.
*   `moderate_message`: 메시지를 삭제하고 선택적으로 사용자 타임아웃을 적용합니다.
*   `judge_conversation_ending`: 메시지가 대화를 종료하는 내용인지 판단하고 적절한 이모지로 응답합니다.

**사용자 관리:**
*   `get_user_info`: 디스코드 사용자 정보를 조회합니다.
*   `change_nickname`: 서버 내 사용자의 닉네임을 변경합니다.
*   `kick_member`: 서버에서 멤버를 추방합니다.
*   `ban_member`: 서버에서 멤버를 차단합니다.

## 사용법

1. 채팅 채널 설정 (관리자 전용)
   - `/addchatchannel` 명령으로 현재 채널을 AI 응답 채널로 등록
   - `/removechatchannel` 명령으로 채널 제거
   - `/listchannels` 명령으로 등록된 채널 목록 확인

2. 봇과 대화하기
   - 등록된 채널에서 봇을 언급하거나 질문 형태의 메시지 입력
   - 봇은 메시지가 자신에게 보내는 것인지 판단 후 응답
   - 예: "괴상한봇아, 새 역할을 만들어줘" 또는 "ㅇㅇㅇ에 대해 검색해줘"

3. 서버 관리 요청하기
   - 등록된 채널에서 봇에게 디스코드 관리 작업 요청
   - 예: "새로운 채널을 만들어줘", "이 메시지에 반응 추가해줘"

4. 메시지가 봇에게 보내지는 것인지 판단
   - 메시지가 봇에게 보내지는 것인지 판단하는 기능이 있어 명령투로 말하거나 봇 이름을 언급하면 봇이 응답합니다.
   - 예: "괴상한봇아, 새 역할을 만들어줘" 또는 "ㅇㅇㅇ에 대해 검색해줘"

## OpenAI MCP 연동 방식

이 봇은 OpenAI Chat Completions API와 MCP 툴을 조합하여 사용자 요청을 처리합니다.

1.  **초기 설정**:
    *   사용자 메시지(`message`)와 프롬프트(`prompt`)를 기반으로 대화 기록(`initial_conversation`)을 준비합니다. 이미지 입력(`img_mode`)도 지원합니다.
    *   기본 시스템 프롬프트에 현재 날짜, 서버 정보(ID, 이름), 채널 정보(ID, 이름), 사용자 ID, 메시지 ID를 추가하여 모델에 컨텍스트를 제공합니다.
    *   `services/mcp.py`에서 사용 가능한 MCP 툴 목록(`get_openai_mcp_tools`)을 OpenAI Function 형식으로 불러옵니다.
    *   `services/mcp.set_current_message(message)`로 현재 Discord 메시지를 MCP 모듈에 전달해 서버/채널 정보를 자동 주입합니다.

2.  **OpenAI 호출 및 툴 사용 루프 (`services/openai_mcp.chat_with_openai_mcp`)**:
    *   최대 50회 `client.chat.completions.create`를 호출합니다.
    *   응답에 텍스트가 포함되면 Discord 메시지를 실시간으로 업데이트합니다.
    *   응답에 `tool_calls`가 있으면:
        *   사용자에게 실행 중인 툴 이름을 알립니다.
        *   `services/openai_mcp.execute_tool`을 통해 MCP 툴을 실행합니다. 내부적으로 `services/mcp.call_tool`을 호출하여 실제 Discord 작업을 수행합니다.
        *   `generate_image` 툴은 `services.openai_mcp.image_generate`로 DALL-E 이미지를 생성하고 Discord에 임베드로 표시합니다.
        *   툴 실행 결과는 `role: tool` 메시지로 대화 기록에 추가되어 이어지는 OpenAI 호출의 컨텍스트로 사용됩니다.
    *   툴 호출이 없을 경우 루프를 종료합니다.

3.  **최종 응답 및 오류 처리**:
    *   마지막 텍스트 응답이 Discord에 표시되며, 응답이 비어 있어도 툴 실행 상태를 사용자에게 전달합니다.
    *   API 호출 또는 툴 실행 중 오류가 발생하면 Discord에 오류 메시지를 표시하고 처리를 중단합니다.

## 스크린샷
![image](https://github.com/user-attachments/assets/b86ab831-cf85-4e0b-a697-c5255451ef95)
![image](https://github.com/user-attachments/assets/9725fbee-d2b3-49fc-a16b-1dd51a1ae48e)
![image](https://github.com/user-attachments/assets/be0d5b6e-9b5a-4817-9838-d257261dec06)
![image](https://github.com/user-attachments/assets/f9323fc7-1c1f-4dac-afc7-3eeda989a4ef)


