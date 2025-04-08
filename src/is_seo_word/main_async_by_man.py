import asyncio
import time
from pathlib import Path
from tqdm import tqdm
from typing import List, Optional

from .async_api import async_get_ai_response, async_get_ai_rsp,async_get_ai_response
from .utils import get_keyword
from .datebase.curd import CURD
from .datebase.models import KeywordSeoScore,KeywordBuyScore
from .models import KeywordScore
from tkzs_bd_db_tool import get_session

# 异步安全的列表操作
class AsyncSafeList:
    def __init__(self):
        self.items = []
        self.lock = asyncio.Lock()
    
    async def append(self, item):
        async with self.lock:
            self.items.append(item)
    
    async def extend(self, items):
        async with self.lock:
            self.items.extend(items)
    
    def get_items(self):
        return list(self.items)
    
    def clear(self):
        self.items.clear()

# 异步进度监控类
class AsyncProgressMonitor:
    def __init__(self, total):
        self.total = total
        self.completed = 0
        self.lock = asyncio.Lock()
        self.pbar = tqdm(total=total, desc="处理关键词")
    
    async def update(self, n=1):
        async with self.lock:
            self.completed += n
            self.pbar.update(n)
            return self.completed
    
    def close(self):
        self.pbar.close()



async def async_db_insert(client: CURD, buffer_items: List[KeywordScore]):
    """异步包装数据库插入操作"""
    # 由于数据库操作可能是阻塞的，使用线程池执行
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: client.bulck_insert_keyword_buy_score(buffer_items))
    print(f"已批量插入{len(buffer_items)}个关键词")

async def main_async(max_concurrency=20, batch_size=50):
    """异步版本的主函数"""
    start_time = time.time()
    file_path = Path(__file__).parent.parent.parent.joinpath("data", "keyword.txt")
    fail_save_path = Path(__file__).parent.parent.parent.joinpath("data", "fail_keyword_async.txt")
    
    # 初始化数据库客户端
    client = CURD()
    
    # 获取关键词列表
    local_keyword_list = get_keyword(file_path)
    
    
    with get_session() as session:
        rsp = session.query(KeywordBuyScore).all()
        db_keyword_list = [item.keyword for item in rsp]
    keywords_list = [keyword for keyword in local_keyword_list if keyword not in db_keyword_list]
    total = len(keywords_list)
    print(f'一共有{total}个关键词,需要打分')
    

    


    
    # 使用信号量控制并发数量
    semaphore = asyncio.Semaphore(max_concurrency)
    print(f"使用协程模式，并发数：{max_concurrency}，批处理大小：{batch_size}")

    # 创建任务列表
    tasks = []

    
    # 分批处理关键词
    async def process_with_semaphore(keyword):
        async with semaphore:
            return await async_get_ai_response(keyword)
    
    # 创建所有任务
    tasks = [process_with_semaphore(keyword) for keyword in keywords_list]
    # 并发执行所有任务
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f'正在处理第{i}个任务')
        # 等待所有任务完成
        results = await asyncio.gather(*batch)
        # 处理结果并插入数据库
        keyword_result  = [item for item in results if isinstance(item, KeywordScore)]
        if keyword_result:
            await async_db_insert(client, keyword_result)


        

    
    end_time = time.time()
    print(f"异步处理总耗时: {end_time - start_time:.2f}秒")
    

