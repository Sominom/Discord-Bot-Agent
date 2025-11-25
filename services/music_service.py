import os
import asyncio
import base64
import json
import requests
import discord
from discord import FFmpegPCMAudio
import yt_dlp as youtube_dl
from googleapiclient.discovery import build
from core.logger import logger
from core.config import env
from mcp_server.context import global_context

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.playing_file_path = ""

    def add(self, item):
        self.queue.append(item)

    def pop(self):
        if not self.is_empty():
            return self.queue.pop(0)
        return None

    def remove_at(self, index):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)
            return True
        return False

    def is_empty(self):
        return len(self.queue) == 0

    def get_list(self):
        return self.queue
    
    def set_playing_file(self, filepath):
        self.playing_file_path = filepath

    def get_playing_file(self):
        return self.playing_file_path

class MusicService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MusicService, cls).__new__(cls)
            cls._instance.queues = {} # guild_id -> MusicQueue
            cls._instance.youtube = None
            cls._instance._init_youtube()
        return cls._instance

    def _init_youtube(self):
        if env.GOOGLE_API_KEY:
            try:
                self.youtube = build('youtube', 'v3', developerKey=env.GOOGLE_API_KEY)
                logger.log("YouTube Data API 클라이언트 초기화 완료", logger.INFO)
            except Exception as e:
                logger.log(f"YouTube 클라이언트 초기화 실패: {e}", logger.ERROR)
        else:
            logger.log("GOOGLE_API_KEY가 설정되지 않아 YouTube 검색을 사용할 수 없습니다.", logger.WARNING)

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def join_voice(self, channel):
        if channel.guild.voice_client:
            if channel.guild.voice_client.channel.id == channel.id:
                return channel.guild.voice_client
            await channel.guild.voice_client.move_to(channel)
            return channel.guild.voice_client
        
        voice_client = await channel.connect()
        return voice_client

    async def leave_voice(self, guild):
        if guild.voice_client:
            await guild.voice_client.disconnect()
            return True
        return False

    async def search_video(self, query):
        if query.startswith("http"):
            return query
        
        if not self.youtube:
            logger.log("YouTube 클라이언트가 초기화되지 않았습니다.", logger.ERROR)
            return None

        try:
            # YouTube Data API v3 검색
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.youtube.search().list(
                    q=query,
                    part='id,snippet',
                    maxResults=1,
                    type='video'
                ).execute()
            )

            if response.get('items'):
                video_id = response['items'][0]['id']['videoId']
                return f"https://www.youtube.com/watch?v={video_id}"
                
        except Exception as e:
            logger.log(f"유튜브 검색 실패: {e}", logger.ERROR)
        return None

    async def add_to_queue(self, guild_id, url):
        queue = self.get_queue(guild_id)
        queue.add(url)

    async def play_next(self, guild):
        queue = self.get_queue(guild.id)
        if queue.is_empty():
            return

        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        if voice_client.is_playing():
            return

        video_url = queue.pop()
        if not video_url:
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': 'True',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

        try:
            loop = asyncio.get_event_loop()
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(video_url, download=True))
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                mp3_filename = base + ".mp3"
                if not os.path.exists(mp3_filename) and os.path.exists(filename):
                       mp3_filename = filename

            queue.set_playing_file(mp3_filename)
            
            client = global_context.get_client()
            
            def after_playing(e):
                if e:
                    logger.log(f"재생 오류: {e}", logger.ERROR)
                future = asyncio.run_coroutine_threadsafe(self.play_next(guild), client.loop)
                try:
                    future.result()
                except Exception as exc:
                    logger.log(f"다음 곡 재생 실패: {exc}", logger.ERROR)
                
                self._safe_remove(mp3_filename)

            voice_client.play(FFmpegPCMAudio(executable="ffmpeg", source=mp3_filename), after=after_playing)
            
        except Exception as e:
            logger.log(f"음악 재생 실패: {str(e)}", logger.ERROR)
            await self.play_next(guild)

    async def stop_music(self, guild):
        if guild.voice_client and guild.voice_client.is_playing():
            guild.voice_client.stop()
            return True
        return False

    async def skip_music(self, guild):
        if guild.voice_client and guild.voice_client.is_playing():
            guild.voice_client.stop()
            return True
        return False

    async def tts(self, guild, text):
        # Google Cloud TTS REST API 사용 (API Key 인증)
        api_key = env.GOOGLE_API_KEY
        if not api_key:
            logger.log("TTS 실패: GOOGLE_API_KEY가 설정되지 않았습니다.", logger.WARNING)
            return
            
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        if voice_client.is_playing():
            return

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "input": {"text": text},
            "voice": {"languageCode": "ko-KR", "ssmlGender": "NEUTRAL"},
            "audioConfig": {"audioEncoding": "MP3"}
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, headers=headers, json=data)
            )
            
            if response.status_code != 200:
                logger.log(f"TTS API 오류 ({response.status_code}): {response.text}", logger.ERROR)
                return

            response_json = response.json()
            audio_content = response_json.get("audioContent")
            
            if not audio_content:
                logger.log("TTS 응답에 오디오 컨텐츠가 없습니다.", logger.ERROR)
                return

            audio_data = base64.b64decode(audio_content)
            
            filename = f"downloads/tts_{guild.id}_{int(loop.time())}.mp3"
            with open(filename, "wb") as out:
                out.write(audio_data)

            voice_client.play(
                FFmpegPCMAudio(filename),
                after=lambda e: self._safe_remove(filename)
            )
        except Exception as e:
            logger.log(f"TTS 오류: {e}", logger.ERROR)

    def _safe_remove(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

music_service = MusicService()
