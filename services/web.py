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
executor = ThreadPoolExecutor(max_workers=2)

# 크롤링용 헤더 설정
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}
custom_search_engine_id = env.CUSTOM_SEARCH_ENGINE_ID
google_api_key = env.GOOGLE_API_KEY

async def search_google(query):
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


def extract_text_from_soup(soup):
    """BeautifulSoup 객체에서 텍스트를 효율적으로 추출"""
    # 불필요한 태그 제거
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
        tag.decompose()
    
    # 메인 콘텐츠 영역 우선 탐색
    main_content = None
    content_selectors = [
        'main', 'article', '[role="main"]', '.content', '.main-content', 
        '.post-content', '.entry-content', '.article-content', '#content',
        '.container .row', '.content-wrapper'
    ]
    
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    # 메인 콘텐츠가 없으면 body 사용
    if not main_content:
        main_content = soup.find('body') or soup
    
    # 텍스트 추출 - 다양한 태그에서 추출
    text_elements = main_content.find_all([
        'p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'li', 'td', 'th', 'blockquote', 'pre', 'code'
    ])
    
    texts = []
    for element in text_elements:
        element_text = element.get_text(strip=True)
        if element_text and len(element_text) > 10:  # 너무 짧은 텍스트 제외
            texts.append(element_text)
    
    # 중복 제거 및 정리
    unique_texts = []
    seen = set()
    for text in texts:
        if text not in seen and len(text) > 20:  # 중복 및 너무 짧은 텍스트 제거
            unique_texts.append(text)
            seen.add(text)
    
    final_text = ' '.join(unique_texts)
    # 공백 정리
    final_text = re.sub(r'\s+', ' ', final_text).strip()
    
    return final_text


async def crawl_website(session, url, timeout_seconds=15):
    try:
        # 웹 페이지 내용 가져오기
        async def fetch_content():
            async with session.get(str(url), headers=DEFAULT_HEADERS, allow_redirects=True) as response:
                # 상태 코드 확인
                if response.status >= 400:
                    logger.log(f"HTTP 오류 {response.status}: {url}", logger.WARNING)
                    return None
                
                # Content-Type 확인
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                    logger.log(f"HTML이 아닌 콘텐츠: {content_type} - {url}", logger.WARNING)
                    return None
                
                raw_response = await response.read()
                
                # 인코딩 감지 및 디코딩
                encoding = None
                charset = response.charset
                if charset:
                    encoding = charset
                else:
                    detected = detect(raw_response)
                    if detected and detected['confidence'] > 0.7:
                        encoding = detected['encoding']
                
                if encoding is None:
                    encoding = 'utf-8'
                
                try:
                    content = raw_response.decode(encoding, errors='ignore')
                except (UnicodeDecodeError, LookupError):
                    content = raw_response.decode('utf-8', errors='ignore')
                
                return content
                
        content = await asyncio.wait_for(fetch_content(), timeout=timeout_seconds)
        
        if not content:
            return None
        
        # BeautifulSoup으로 HTML 파싱
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(executor, BeautifulSoup, content, 'html.parser')
        
        # 효율적인 텍스트 추출
        text = await loop.run_in_executor(executor, extract_text_from_soup, soup)
        
        # 최소 길이 확인
        if len(text) < 200:
            logger.log(f"추출된 텍스트가 너무 짧음 ({len(text)}자): {url}", logger.WARNING)
            return None
        
        max_len = 20000
        # 최대 길이 제한 (너무 긴 텍스트 방지)
        if len(text) > max_len:
            text = text[:max_len] + "..."
            
        return text
        
    except asyncio.TimeoutError:
        logger.log(f"크롤링 타임아웃: {url}", logger.WARNING)
        return None
    except Exception as e:
        logger.log(f"크롤링 실패: {url} - {str(e)}", logger.ERROR)
        return None


async def search_and_crawl(keyword):
    tasks = []
    
    # 검색 실행
    search_urls = await search_google(keyword)
    if search_urls:
        search_result = ""
        
        # 검색 결과 각 페이지 크롤링
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
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