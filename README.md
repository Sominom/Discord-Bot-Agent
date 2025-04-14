
## 기능
- Claude와 실시간 대화
- DALL-E를 통한 이미지 생성
- 디스코드 채널 관리 기능 (MCP 통합)
- 역할 관리, 메시지 관리 등 다양한 디스코드 관리 기능
- 메시지 분류: 봇에게 보내는 메시지인지 자동 판단 (OpenAI)

## 설치 및 실행

1. 의존성 설치
```bash
pip install -r requirements.txt
```

2. `.env` 파일 설정
```
# 필수 설정
DISCORD_BOT_KEY=your_discord_bot_token
DISCORD_OWNER_ID=your_discord_id

# API 키 설정
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key

# 모델 설정 (GPT 모델은 system 프롬프트가 지원되는 모델이어야 합니다. -- 추후 수정 예정)
OPENAI_MODEL=gpt-4-turbo
CLAUDE_MODEL=claude-3-opus-20240229

# 데이터베이스 설정
DATABASE_URL=sqlite:///bot.db
```

3. 봇 실행
```bash
python bot.py
```

## MCP(Model Context Protocol) 통합

디스코드 인터페이스와 AI 모델 간의 상호작용을 위한 MCP(Model Context Protocol) 서버를 구현합니다.
이 프로젝트는 채팅으로 디스코드 서버 관리 기능을 자동화합니다.
추가로 이미지 생성, 검색 등의 기능도 사용할 수 있습니다.

시스템 구성:
- MCP 서버는 Discord 애플리케이션과 동일한 프로세스에서 실행되며, WebSocket 기반 통신을 제공합니다.
- 채팅 입력시 상대적으로 저렴한 GPT-4o-mini 모델로 최근 채팅 내용을 분석하여 봇에게 채팅 요청을 하는지 판단하여 Claude 모델로 전달합니다.
- Claude 모델이 사용자 의도를 분석하여 적절한 MCP 도구를 선택 및 실행하고, 일반적인 대화도 가능합니다.
- 디스코드 채팅 인터페이스가 MCP 클라이언트 역할을 수행하여 사용자와 시스템 간 상호작용을 중개합니다.

복잡한 디스코드 서버 관리 작업을 단순한 채팅 명령으로 수행할 수 있게 하여 관리 효율성을 크게 향상시킵니다.

## 사용 가능한 MCP 도구 목록

다음은 현재 봇에서 사용할 수 있는 MCP 도구 목록입니다:

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

## Claude 연동 방식

이 봇은 Anthropic의 Claude 모델과 상호작용하여 사용자 요청을 처리하고 대화를 진행합니다.

1.  **초기 설정**:
    *   사용자 메시지(`message`)와 프롬프트(`prompt`)를 기반으로 대화 기록(`initial_conversation`)을 준비합니다. 이미지 입력(`img_mode`)도 지원합니다.
    *   기본 시스템 프롬프트에 현재 날짜, 서버 정보(ID, 이름), 채널 정보(ID, 이름), 사용자 ID, 메시지 ID를 추가하여 Claude에게 컨텍스트를 제공합니다.
    *   `services/mcp.py`에서 사용 가능한 MCP 도구 목록(`mcp_tools`)을 가져옵니다.
    *   `services/mcp.set_current_message(message)`를 호출하여 현재 처리 중인 Discord 메시지 객체를 MCP 모듈에 전달합니다. 이는 일부 MCP 도구가 메시지 컨텍스트(예: 서버 ID 자동 추출)를 활용하기 위함입니다.

2.  **Claude API 호출 및 도구 사용 루프**:
    *   봇은 최대 50번의 상호작용(`current_round`)을 통해 Claude와 대화하며 도구를 사용합니다.
    *   각 라운드마다 현재까지의 대화 기록(`messages`)과 사용 가능한 MCP 도구 목록(`mcp_tools`)을 포함하여 Claude API(`claude_client.messages.create`)를 호출합니다. 이 호출은 스트리밍 방식이 아닌, 한 번에 완전한 응답을 받는 방식입니다.
    *   Claude의 응답(`response.content`)에는 텍스트 응답과 도구 사용 요청(`tool_use`)이 포함될 수 있습니다.
    *   **텍스트 응답 처리**: 응답에 텍스트가 포함되어 있으면, 해당 텍스트(`latest_text_response`)로 Discord의 응답 메시지를 업데이트합니다.
    *   **도구 사용 처리**:
        *   응답에 도구 사용 요청(`tool_calls_in_response`)이 있으면, 각 요청된 도구(`tool_call`)에 대해 다음을 수행합니다:
            *   Discord 메시지를 업데이트하여 사용자에게 어떤 도구를 호출하는지 알립니다.
            *   `services/claude.execute_tool` 함수를 호출하여 해당 MCP 도구를 실행합니다. `message.id`도 함께 전달되어 도구 실행 시 컨텍스트로 활용될 수 있습니다.
            *   `generate_image` 도구는 특별히 처리되어, `services.claude.image_generate` 함수를 직접 호출하여 DALL-E 이미지를 생성하고 Discord 메시지에 임베드로 표시합니다.
            *   다른 MCP 도구들은 `services/mcp.call_tool` 함수를 통해 실행됩니다.
            *   도구 실행 결과를 Discord 메시지에 업데이트합니다.
        *   성공적인 도구 실행 결과는 다음 Claude API 호출 시 컨텍스트로 제공하기 위해 `user` 역할의 메시지로 대화 기록(`messages`)에 추가됩니다.
    *   도구 사용 요청이 없을 경우 루프를 종료합니다.

3.  **최종 응답 및 오류 처리**:
    *   도구 사용 루프가 종료되면 (도구 호출이 더 이상 없거나 최대 라운드 도달), 마지막으로 받은 텍스트 응답이 Discord에 표시됩니다.
    *   만약 텍스트 응답 없이 도구 실행만 완료된 경우, "도구 실행은 완료되었지만 응답이 없습니다."와 같은 메시지를 표시합니다.
    *   API 호출 또는 도구 실행 중 오류가 발생하면 해당 오류 메시지를 Discord에 표시하고 처리를 중단합니다.

## 스크린샷
![image](https://github.com/user-attachments/assets/b86ab831-cf85-4e0b-a697-c5255451ef95)
![image](https://github.com/user-attachments/assets/9725fbee-d2b3-49fc-a16b-1dd51a1ae48e)
![image](https://github.com/user-attachments/assets/be0d5b6e-9b5a-4817-9838-d257261dec06)
![image](https://github.com/user-attachments/assets/f9323fc7-1c1f-4dac-afc7-3eeda989a4ef)


