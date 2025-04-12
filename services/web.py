"""
웹 검색 및 크롤링 기능을 제공하는 모듈
Google Custom Search API를 사용한 검색과 BeautifulSoup을 사용한 웹 페이지 크롤링을 제공합니다.
"""

from concurrent.futures import ThreadPoolExecutor
import aiohttp
import asyncio
import json
import urllib.parse
import re
from bs4 import BeautifulSoup
from chardet import detect
from core.logger import logger
from core.config import env

# 스레드 풀 설정
executor = ThreadPoolExecutor(max_workers=1)
custom_search_engine_id = env.CUSTOM_SEARCH_ENGINE_ID
google_api_key = env.GOOGLE_API_KEY

async def search_google(query):
    """
    Google Custom Search API를 사용하여 검색 결과를 가져옵니다.
    
    Args:
        query: 검색할 키워드 (문자열 또는 리스트)
        
    Returns:
        검색 결과 목록 또는 실패 시 None
    """

    query_list = []

    search_num = 2

    encoded_query = urllib.parse.quote(str(query))
    query_list.append(encoded_query)
    
    return_result = []
    
    # 검색 실행
    for q in query_list:
        url = f"https://www.googleapis.com/customsearch/v1?cx={custom_search_engine_id}&key={google_api_key}&q={q}&num={search_num}"
        logger.log(f"검색 쿼리: {url}", logger.INFO)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.text()
        
        try:
            result = json.loads(result)
            if 'items' in result:
                filtered_items = [item for item in result['items']]
                return_result = filtered_items
        except Exception as e:
            logger.log(f"검색 결과 파싱 실패: {str(e)}", logger.ERROR)
            return None
            
    return return_result


async def crawl_website(session, url, timeout_seconds=15):
    """
    웹 페이지를 크롤링하여 텍스트 내용을 추출합니다.
    
    Args:
        session: aiohttp 세션 객체
        url: 크롤링할 웹 페이지 주소
        timeout_seconds: 타임아웃 시간(초)
        
    Returns:
        추출된 텍스트 또는 실패 시 None
    """
    try:
        # 웹 페이지 내용 가져오기
        async def fetch_content():
            async with session.get(str(url)) as response:
                raw_response = await response.read()
                encoding = detect(raw_response)['encoding']
                if encoding is None:
                    encoding = 'utf-8'
                content = raw_response.decode(encoding, errors='ignore')
                return content
                
        content = await asyncio.wait_for(fetch_content(), timeout=timeout_seconds)
        
        # BeautifulSoup으로 HTML 파싱
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(executor, BeautifulSoup, content, 'html.parser')
        
        # 텍스트 추출
        body = soup.find('body')
        p_tags = body.find_all('p')
        text = "".join([tag.get_text() for tag in p_tags])
        text = re.sub(r'\s+', ' ', text)
        
        # 너무 짧은 내용은 무시
        if len(text) < 500:
            return None
            
        return text
    except Exception:
        logger.log(f"크롤링 실패: {url}", logger.ERROR)
        return None


async def search_and_crawl(keyword):
    """
    키워드로 검색 후 결과 페이지를 크롤링하여 내용을 반환합니다.
    
    Args:
        keyword: 검색할 키워드
        
    Returns:
        크롤링된 내용 또는 실패 시 None
    """
    tasks = []
    
    # 검색 실행
    search_urls = await search_google(keyword)
    if search_urls:
        search_result = ""
        
        # 검색 결과 각 페이지 크롤링
        async with aiohttp.ClientSession() as session:
            for search_item in search_urls:
                logger.log(f"검색 결과 크롤링: {search_item['link']}", logger.INFO)
                task = asyncio.ensure_future(crawl_website(session, search_item['link']))
                tasks.append(task)
                
            responses = await asyncio.gather(*tasks)
            
            # 크롤링 결과 정리
            i = 1
            for response in responses:
                if response:
                    search_result += f"{i}. {response}\n"
                    i += 1
                    
        logger.log(f"크롤링 완료: {len(search_result)}자 추출", logger.INFO)
        return search_result
    else:
        return None 