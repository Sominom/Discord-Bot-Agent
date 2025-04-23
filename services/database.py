import json
import os
from core.logger import logger

DATA_FILE = "data.json"

def _load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"chat_channels": [], "settings": {}}
        _save_data(default_data)
        logger.log(f"데이터 파일 생성: {DATA_FILE}", logger.INFO)
        return default_data
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.log(f"데이터 로드 오류 ({DATA_FILE}): {e}", logger.ERROR)
        default_data = {"chat_channels": [], "settings": {}}
        _save_data(default_data)
        return default_data

def _save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logger.log(f"데이터 저장 오류 ({DATA_FILE}): {e}", logger.ERROR)

def get_chat_channels():
    data = _load_data()
    return data.get("chat_channels", [])

def add_chat_channel(channel_id, guild_id, name):
    data = _load_data()
    if "chat_channels" not in data:
        data["chat_channels"] = []
        
    if channel_id not in data["chat_channels"]:
        data["chat_channels"].append(channel_id)
        _save_data(data)
        logger.log(f"채널 추가됨: {channel_id} ({name})", logger.INFO)
        return True
    else:
        logger.log(f"채널 {channel_id}는 이미 존재합니다.", logger.WARNING)
        return True # 이미 존재해도 성공으로 간주

def delete_chat_channel(channel_id):
    data = _load_data()
    if "chat_channels" in data and channel_id in data["chat_channels"]:
        data["chat_channels"].remove(channel_id)
        _save_data(data)
        logger.log(f"채널 삭제됨: {channel_id}", logger.INFO)
        return True
    else:
        logger.log(f"삭제할 채널 {channel_id}를 찾을 수 없습니다.", logger.WARNING)
        return False

def get_setting(name, default=None):
    data = _load_data()
    return data.get("settings", {}).get(name, default)

def set_setting(name, value):
    data = _load_data()
    if "settings" not in data:
        data["settings"] = {}
    data["settings"][name] = value
    _save_data(data)
    logger.log(f"설정값 저장됨: {name}={value}", logger.INFO)
    return True

__all__ = [
    "get_chat_channels",
    "add_chat_channel",
    "delete_chat_channel",
    "get_setting",
    "set_setting"
] 