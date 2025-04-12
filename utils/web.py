from concurrent.futures import ThreadPoolExecutor
import aiohttp
import asyncio
import json
import urllib.parse
import traceback
import re
import aiohttp
from bs4 import BeautifulSoup
from chardet import detect
from data.config import Config
from data.bot_logger import BotLogger

config = Config()
logger = BotLogger()

executor = ThreadPoolExecutor(max_workers=1)
custom_search_engine_id = config.custom_search_engine_id
google_api_key = config.google_api_key
forbidden_domains = config.forbidden_domains
forbidden_search_keywords = config.forbidden_search_keywords

async def search_google(query, forbidden_domains=[], forbidden_search_keywords=[]):
    forbidden_domains = " ".join([f"-site:{site}" for site in forbidden_domains])
    forbidden_search_keywords = " ".join([f"-{keyword}" for keyword in forbidden_search_keywords])
    query_list = []

    search_num = 2
    if isinstance(query, str):
        query =  query + " " + forbidden_domains + " " + forbidden_search_keywords
        encoded_query = urllib.parse.quote(str(query))
        query_list.append(encoded_query)

    elif isinstance(query, list):
        for q in query:
            q =  q + " " + forbidden_domains + " " + forbidden_search_keywords
            encoded_query = urllib.parse.quote(str(q))
            query_list.append(encoded_query)
    else:
        query = ''.join(query)
        query =  query + " " + forbidden_domains + " " + forbidden_search_keywords
        encoded_query = urllib.parse.quote(str(query))
        query_list.append(encoded_query)
        
    returnResult = []
    
    for q in query_list:
        url = f"https://www.googleapis.com/customsearch/v1?cx={custom_search_engine_id}&key={google_api_key}&q={q}&num={search_num}"
        logger.log(f"Search: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.text()
        try:
            result = json.loads(result)
            if 'items' in result:
                filtered_items = [item for item in result['items']]
                returnResult = filtered_items
        except Exception as e:
            logger.log(f"검색 결과 파싱 실패 {str(e)}", logger.ERROR)
            return None
    return returnResult


async def crawl_website(session, url, timeout_seconds=15):
    try:
        async def fetch_content():
            async with session.get(str(url)) as response:
                raw_response = await response.read()
                encoding = detect(raw_response)['encoding']
                if encoding is None:
                    encoding = 'utf-8'
                content = raw_response.decode(encoding, errors='ignore')
                return content
        content = await asyncio.wait_for(fetch_content(), timeout=timeout_seconds)
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(executor, BeautifulSoup, content, 'html.parser')
        body = soup.find('body')
        p_tags = body.find_all('p')
        text = "".join([tag.get_text() for tag in p_tags])
        text = re.sub(r'\s+', ' ', text)
        
        if len(text) < 500:
            return None
        return text
    except Exception:
        logger.log(f"크롤링 실패 {url}", logger.ERROR)
        return None

async def search_and_crawl(keyword):
    tasks = []
    search_urls = await search_google(keyword)
    if search_urls:
        search_result = ""
        async with aiohttp.ClientSession() as session:
            for search_item in search_urls:
                logger.log(f"검색 결과: {search_item['link']}")
                task = asyncio.ensure_future(crawl_website(session, search_item['link']))
                tasks.append(task)
            responses = await asyncio.gather(*tasks)
            i = 1
            for response in responses:
                if response:
                    search_result += f"{i}. {response}\n"
                    i += 1
        logger.log(f"크롤링 결과: {search_result}", logger.INFO)
        return search_result
    else:
        return None