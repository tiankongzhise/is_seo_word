import asyncio
import time
from pathlib import Path
from tqdm import tqdm
from typing import List, Optional

from .async_api import async_get_ai_response, async_get_ai_rsp
from .utils import get_keyword
from .datebase.curd import CURD
from .models import KeywordScore

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

async def process_keyword(keyword, responses, fail_keywords, progress_monitor):
    """处理单个关键词的异步函数"""
    try:
        # 直接使用异步函数获取AI响应
        ai_response = await async_get_ai_rsp(keyword)
        await responses.append(ai_response)
        await progress_monitor.update()
        return ai_response
    except Exception as e:
        print(f"获取AI响应失败：{e}，关键词：{keyword}")
        await fail_keywords.append(keyword)
        await progress_monitor.update()
        return None

async def batch_process(batch: List[str], responses, fail_keywords, progress_monitor):
    """批量处理关键词的异步函数"""
    tasks = [process_keyword(keyword, responses, fail_keywords, progress_monitor) for keyword in batch]
    return await asyncio.gather(*tasks, return_exceptions=True)

async def async_db_insert(client: CURD, buffer_items: List[KeywordScore]):
    """异步包装数据库插入操作"""
    # 由于数据库操作可能是阻塞的，使用线程池执行
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: client.bluck_insert_keyword_seo_score(buffer_items))
    print(f"已批量插入{len(buffer_items)}个关键词")

async def main_async(max_concurrency=20, batch_size=50):
    """异步版本的主函数"""
    start_time = time.time()
    file_path = Path(__file__).parent.parent.parent.joinpath("data", "keyword.txt")
    fail_save_path = Path(__file__).parent.parent.parent.joinpath("data", "fail_keyword_async.txt")
    
    # 获取关键词列表
    keywords_list = get_keyword(file_path)
    total = len(keywords_list)
    
    # 初始化异步安全的数据结构
    responses = AsyncSafeList()
    fail_keywords = AsyncSafeList()
    buffer = AsyncSafeList()
    
    # 初始化数据库客户端
    client = CURD()
    
    # 初始化进度监控
    progress_monitor = AsyncProgressMonitor(total)

    
    # 使用信号量控制并发数量
    semaphore = asyncio.Semaphore(max_concurrency)
    print(f"使用协程模式，并发数：{max_concurrency}，批处理大小：{batch_size}")

    # 创建任务列表
    tasks = []
    db_tasks = []
    
    # 分批处理关键词
    for i in range(0, len(keywords_list), batch_size):
        print(f"开始处理第{i+1}到{i+batch_size}个关键词")
        batch = keywords_list[i:i+batch_size]
        tasks.append(batch_process(batch, responses, fail_keywords, progress_monitor))

        print(f"任务提交完毕,等待所有任务完成")

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
    
    # 处理结果并插入数据库
    all_results = [item for sublist in results for item in sublist if isinstance(item, KeywordScore)]
    if all_results:
        await async_db_insert(client, all_results)
    
    # 关闭进度条
    progress_monitor.close()
    
    # 保存失败的关键词
    fail_items = fail_keywords.get_items()
    if fail_items:
        with open(fail_save_path, "w", encoding="utf-8") as f:
            for keyword in fail_items:
                f.write(keyword + "\n")
        print(f"有{len(fail_items)}个关键词处理失败，已保存到{fail_save_path}")
    
    end_time = time.time()
    print(f"异步处理总耗时: {end_time - start_time:.2f}秒")
    
    # 返回所有响应
    return responses.get_items()

# 兼容原有调用方式
def main():
    return asyncio.run(main_async())

# 混合模式：结合多线程和协程
async def hybrid_process_batch(batch, thread_pool_executor, responses, fail_keywords, progress_monitor):
    """使用线程池处理CPU密集型任务，使用协程处理IO密集型任务"""
    loop = asyncio.get_event_loop()
    tasks = []
    
    for keyword in batch:
        # 使用协程处理IO密集型任务（网络请求）
        task = asyncio.create_task(process_keyword(keyword, responses, fail_keywords, progress_monitor))
        tasks.append(task)
    
    return await asyncio.gather(*tasks, return_exceptions=True)

async def main_hybrid(max_workers=10, max_concurrency=20, batch_size=50):
    """混合版本的主函数，结合多线程和协程"""
    import concurrent.futures
    
    start_time = time.time()
    file_path = Path(__file__).parent.parent.parent.joinpath("data", "keyword.txt")
    fail_save_path = Path(__file__).parent.parent.parent.joinpath("data", "fail_keyword_hybrid.txt")
    
    # 获取关键词列表
    keywords_list = get_keyword(file_path)
    total = len(keywords_list)
    
    # 初始化异步安全的数据结构
    responses = AsyncSafeList()
    fail_keywords = AsyncSafeList()
    
    # 初始化数据库客户端
    client = CURD()
    
    # 初始化进度监控
    progress_monitor = AsyncProgressMonitor(total)
    
    # 创建线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 分批处理关键词
        tasks = []
        for i in range(0, len(keywords_list), batch_size):
            batch = keywords_list[i:i+batch_size]
            task = hybrid_process_batch(batch, executor, responses, fail_keywords, progress_monitor)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 处理结果并插入数据库
        all_results = [item for sublist in results for item in sublist if isinstance(item, KeywordScore)]
        if all_results:
            await async_db_insert(client, all_results)
    
    # 关闭进度条
    progress_monitor.close()
    
    # 保存失败的关键词
    fail_items = fail_keywords.get_items()
    if fail_items:
        with open(fail_save_path, "w", encoding="utf-8") as f:
            for keyword in fail_items:
                f.write(keyword + "\n")
        print(f"有{len(fail_items)}个关键词处理失败，已保存到{fail_save_path}")
    
    end_time = time.time()
    print(f"混合处理总耗时: {end_time - start_time:.2f}秒")
    
    # 返回所有响应
    return responses.get_items()

def run_hybrid():
    """运行混合版本的入口函数"""
    return asyncio.run(main_hybrid())
