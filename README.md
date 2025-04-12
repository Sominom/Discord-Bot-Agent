# Interactive-GPT-Discord-Bot
디스코드에서 GPT와 대화하고, 이미지 분석 및 생성 기능을 제공하는 봇입니다.

![image](https://github.com/SolusJ/Discord_GPT4o/assets/36412182/2c4a0e8d-009a-4636-9524-3d09888e23d3)

## 주요 기능
- GPT를 통한 인터랙티브 채팅
- DALL-E를 이용한 이미지 생성
- 이미지 분석 및 텍스트 추출
- 웹 검색 및 결과 요약



## 설치 및 실행 (Linux)
```bash
# 저장소 클론
git clone https://github.com/yourusername/Interactive-GPT-Discord-Bot.git
cd Interactive-GPT-Discord-Bot

# 가상환경 설정
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 실행 권한 부여
chmod +x start.sh
./start.sh
```

## 명령어
### 관리자 명령어
- `/addchatchannel` - 현재 채널을 대화 채널로 추가
- `/removechatchannel` - 현재 채널을 대화 채널에서 제거
- `/listchannels` - 대화 채널 목록 표시
- `/reload [extension]` - 봇 확장 기능 다시 로드

### GPT 서비스 명령어
- `/image [prompt] [size]` - DALL-E로 이미지 생성
- `/setmodel [model]` - GPT 모델 변경
- `/modinfo` - 현재 GPT 모델 정보 확인

### 채팅 명령어
- `/clear [amount]` - 채팅방 메시지 청소
- `/historylimit [limit]` - 대화 기록 제한 설정

## 스크린샷
![채팅 기능](https://github.com/SolusJ/Discord_GPT4o/assets/36412182/b540a65c-9e4d-4947-bc95-e8fc07d16d2d)

![이미지 생성](https://github.com/SolusJ/Discord_GPT4o/assets/36412182/1d315839-0cfe-43e8-9258-ea808d1af561)

![이미지 분석](https://github.com/SolusJ/Discord_GPT4o/assets/36412182/c2692ad7-ae3a-41ef-972e-18cef3f4d205)

![웹 검색](https://github.com/SolusJ/Discord_GPT4o/assets/36412182/e8035586-7189-444b-9cf5-91a589374d78)
