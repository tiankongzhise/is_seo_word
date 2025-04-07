import concurrent.futures
import threading
from pathlib import Path
from tqdm import tqdm

from .async_get_ai_rsp import get_ai_rsp_threaded
from .utils import get_keyword
from .datebase.curd import CURD

# 线程安全的列表操作
class ThreadSafeList:
    def __init__(self):
        self.items = []
        self.lock = threading.Lock()
    
    def append(self, item):
        with self.lock:
            self.items.append(item)
    
    def extend(self, items):
        with self.lock:
            self.items.extend(items)
    
    def get_items(self):
        with self.lock:
            return list(self.items)
    
    def clear(self):
        with self.lock:
            self.items.clear()

# 进度监控类
class ProgressMonitor:
    def __init__(self, total):
        self.total = total
        self.completed = 0
        self.lock = threading.Lock()
        self.pbar = tqdm(total=total, desc="处理关键词")
    
    def update(self, n=1):
        with self.lock:
            self.completed += n
            self.pbar.update(n)
            return self.completed
    
    def close(self):
        self.pbar.close()

def process_keyword(keyword, responses, fail_keywords, progress_monitor):
    """处理单个关键词的函数，用于线程池"""
    try:
        # 使用线程池版本的AI响应获取函数
        ai_response = get_ai_rsp_threaded(keyword)
        responses.append(ai_response)
        progress_monitor.update()
        return ai_response
    except Exception as e:
        print(f"获取AI响应失败：{e}，关键词：{keyword}")
        fail_keywords.append(keyword)
        progress_monitor.update()
        return None

def main_threaded(max_workers=10, batch_size=20):
    """多线程版本的主函数"""
    file_path = Path(__file__).parent.parent.parent.joinpath("data", "keyword.txt")
    fail_save_path = Path(__file__).parent.parent.parent.joinpath("data", "fail_keyword.txt")
    
    # 获取关键词列表
    keywords_list = get_keyword(file_path)
    total = len(keywords_list)
    
    # 初始化线程安全的数据结构
    responses = ThreadSafeList()
    fail_keywords = ThreadSafeList()
    buffer = ThreadSafeList()
    
    # 初始化数据库客户端
    client = CURD()
    
    # 初始化进度监控
    progress_monitor = ProgressMonitor(total)
    
    # 使用线程池执行并发请求
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务到线程池
        future_to_keyword = {executor.submit(process_keyword, keyword, responses, fail_keywords, progress_monitor): keyword for keyword in keywords_list}
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_keyword):
            keyword = future_to_keyword[future]
            try:
                result = future.result()
                if result:
                    buffer.append(result)
                    
                    # 当缓冲区达到批处理大小时，执行数据库插入
                    buffer_items = buffer.get_items()
                    if len(buffer_items) >= batch_size:
                        client.bluck_insert_keyword_seo_score(buffer_items)
                        print(f"已批量插入{len(buffer_items)}个关键词")
                        buffer.clear()
            except Exception as e:
                print(f"处理关键词 {keyword} 时发生错误: {e}")
    
    # 处理剩余的缓冲区数据
    buffer_items = buffer.get_items()
    if buffer_items:
        client.bluck_insert_keyword_seo_score(buffer_items)
        print(f"已批量插入剩余的{len(buffer_items)}个关键词")
    
    # 关闭进度条
    progress_monitor.close()
    
    # 保存失败的关键词
    fail_items = fail_keywords.get_items()
    if fail_items:
        with open(fail_save_path, "w", encoding="utf-8") as f:
            for keyword in fail_items:
                f.write(keyword + "\n")
        print(f"有{len(fail_items)}个关键词处理失败，已保存到{fail_save_path}")
    
    # 返回所有响应
    return responses.get_items()

# 兼容原有调用方式
def main():
    return main_threaded()