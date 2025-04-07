import argparse
import time
from pathlib import Path

from .main_threaded import main_threaded
from .main_async import main_async, main_hybrid

def run():
    """命令行入口函数，支持选择不同的并发模式"""
    parser = argparse.ArgumentParser(description="SEO关键词评分工具 - 多种并发模式")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["thread", "async", "hybrid"], 
        default="async",
        help="并发模式：thread=多线程，async=协程，hybrid=混合模式"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=10,
        help="线程池工作线程数量（仅用于thread和hybrid模式）"
    )
    parser.add_argument(
        "--concurrency", 
        type=int, 
        default=10,
        help="最大并发请求数（仅用于async和hybrid模式）"
    )
    parser.add_argument(
        "--batch", 
        type=int, 
        default=100,
        help="批处理大小"
    )
    parser.add_argument(
        "--file", 
        type=str,
        help="关键词文件路径，默认为data/keyword.txt"
    )
    
    args = parser.parse_args()
    
    # 记录开始时间
    start_time = time.time()
    
    # 根据模式选择不同的处理函数
    if args.mode == "thread":
        print(f"使用多线程模式，线程数：{args.workers}，批处理大小：{args.batch}")
        results = main_threaded(max_workers=args.workers, batch_size=args.batch)
    elif args.mode == "async":
        print(f"使用协程模式，并发数：{args.concurrency}，批处理大小：{args.batch}")
        import asyncio
        results = asyncio.run(main_async(max_concurrency=args.concurrency, batch_size=args.batch))
    elif args.mode == "hybrid":
        print(f"使用混合模式，线程数：{args.workers}，并发数：{args.concurrency}，批处理大小：{args.batch}")
        import asyncio
        results = asyncio.run(main_hybrid(max_workers=args.workers, max_concurrency=args.concurrency, batch_size=args.batch))
    
    # 计算总耗时
    end_time = time.time()
    print(f"总耗时: {end_time - start_time:.2f}秒")
    print(f"处理完成，共处理 {len(results)} 个关键词")
    
    return results

if __name__ == "__main__":
    run()