import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .models import KeywordScore
from decimal import Decimal, getcontext
import aiohttp
import time

# 设置全局精度为 4 位
getcontext().prec = 4
load_dotenv()

# 创建一个全局的异步客户端，避免重复创建
_client = None

def get_async_client():
    """获取全局异步客户端实例"""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ.get("ARK_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
    return _client

async def async_get_ai_response(keyword, retries=3, backoff_factor=0.5):
    """真正的异步API调用实现，带有重试机制"""
    client = get_async_client()
    print(f"开始处理关键词: {keyword}")
    for attempt in range(retries):
        try:
            completion = await client.chat.completions.create(
                model="ep-20250407223552-sb9r2",  # your model endpoint ID
                messages=[
                    {"role": "system", "content": "你是一个关键词判别器,对用户输入的关键词进行判别,判断是正常的用户搜索需求,还是SEO工作者生造的无意义拼凑词.值为0-1,越接近1标识越有可能是生造无意义词,越接近0表示越可能是用户的正常搜索习惯,结果只需要回答一个0-1之间的小数,不需要其他内容"},
                    {"role": "user", "content": keyword},
                ],
            )
            rsp = completion.choices[0].message.content
            return KeywordScore(keyword=keyword, score=Decimal(rsp))
        except Exception as e:
            if attempt < retries - 1:
                # 计算退避时间
                wait_time = backoff_factor * (2 ** attempt)
                print(f"尝试 {attempt+1}/{retries} 失败: {e}. 等待 {wait_time:.2f} 秒后重试...")
                await asyncio.sleep(wait_time)
            else:
                # 最后一次尝试失败，抛出异常
                print(f"所有 {retries} 次尝试都失败了: {e}")
                raise

async def process_keywords_batch(keywords, semaphore, max_concurrent=20):
    """使用信号量控制并发处理一批关键词"""
    async def process_with_semaphore(keyword):
        async with semaphore:
            return await async_get_ai_response(keyword)
    
    # 创建所有任务
    tasks = [process_with_semaphore(keyword) for keyword in keywords]
    
    # 并发执行所有任务
    return await asyncio.gather(*tasks, return_exceptions=True)

# 兼容旧版本的异步函数
async def async_get_ai_rsp(keyword):
    """兼容旧版本的异步函数"""
    return await async_get_ai_response(keyword)