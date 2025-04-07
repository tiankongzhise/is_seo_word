import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .models import KeywordScore
from decimal import Decimal, getcontext

# 设置全局精度为 2 位小数
getcontext().prec = 4  # 包含整数位 + 小数位（如 0.12 需要 3 位精度）
load_dotenv()

async def async_get_ai_rsp(keyword, timeout=30):
    """异步获取AI响应"""
    print(f"开始处理关键词: {keyword}")
    start_time = time.time()
    
    try:
        client = AsyncOpenAI(
            api_key=os.environ.get("ARK_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )

        completion = await client.chat.completions.create(
            model="ep-20250407223552-sb9r2",  # your model endpoint ID
            messages=[
                {"role": "system", "content": "你是一个关键词判别器,对用户输入的关键词进行判别,判断是正常的用户搜索需求,还是SEO工作者生造的无意义拼凑词.值为0-1,越接近1标识越有可能是生造无意义词,越接近0表示越可能是用户的正常搜索习惯,结果只需要回答一个0-1之间的小数,不需要其他内容"},
                {"role": "user", "content": keyword},
            ],
            timeout=timeout
        )
        
        rsp = await asyncio.wait_for(completion.choices[0].message.content, timeout=timeout)
        elapsed = time.time() - start_time
        print(f"成功处理关键词: {keyword}, 耗时: {elapsed:.2f}秒")
        return KeywordScore(keyword=keyword, score=Decimal(rsp))
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"获取AI响应超时：{keyword}, 已耗时: {elapsed:.2f}秒")
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"获取AI响应失败：{e}，关键词：{keyword}, 已耗时: {elapsed:.2f}秒")
        raise

# 使用线程池执行异步函数的包装器
def get_ai_rsp_threaded(keyword):
    """线程池版本的AI响应获取函数"""
    import concurrent.futures
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_get_ai_rsp(keyword))
    finally:
        loop.close()