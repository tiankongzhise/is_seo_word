import asyncio
import time
import multiprocessing # Import multiprocessing

from pathlib import Path


# Assuming these imports exist and work as in the original code
from src.is_seo_word.datebase.curd import CURD
from src.is_seo_word.models import FileInfo
from src.is_seo_word.get_ai_rsp_v3 import async_get_ai_rsp # Assuming this can be awaited or adapted
from src.is_seo_word.utils import (get_keyword,
                                   preserve_order_deduplicate, 
                                   save_rsp_v3_result,
                                   saver_process_func,
                                   TERMINATION_SENTINEL,
                                   update_rsp_fail_txt_to_score_with_reason)

# --- Configuration ---
SYSTEM_ROLE_CONTENT = r"""你是一个SEM关键词筛选系统,对用户输入的一个或者一组关键词的每关键词进行判别是否是一个seo生造词,判断的维度为是否出现不合理重复,语法不符合人类语言习惯,逻辑混乱等.评分从0-100,越接近100表示越可能是SEO生造词.不是人类用户的搜索习惯,
输出结果格式为一个标准的json组成的List 格式为[{"关键词":XXXX,"评分":xxxx,"原因":xxxx}],举例用户输入为网络信息安全培训培训,网络安全+渗透+培训,网络网络工程培训机构,网络工程培训培训,网络网络运维,Java培训,软件开发培训 则输出结果为
[{"关键词":"网络信息安全培训培训","评分":80,"原因":"[培训]连续重复,不符合常见语法"},
 {"关键词":"网络安全+渗透+培训","评分":93,"原因":"堆叠关键词,使用的符号[+],并不是正常搜索常见符号,反而是搜索优化常用符号"},
 {"关键词":"网络网络工程培训机构","评分":92,"原因":"[网络]连续重复,且不符合语法,逻辑意义不明"},
 {"关键词":"网络工程培训培训","评分":85,"原因":"[培训]连续重复,语法不符合人类语言习惯"},
 {"关键词":"编程 开发培训学校","评分":63,"原因":"出现[空格],关键词组合稍显生硬"},
 {"关键词":"计算机 开发 学习","评分":92,"原因":"[空格]连续出现,不符合常见输入习惯"},
 {"关键词":"网络网络运维","评分":88,"原因":"[网络]出现重复,分析后不符合逻辑,不具备明确搜索意图"},
 {"关键词":"Java培训","评分":10,"原因":"语法正确,意义明确"},
 {"关键词":"软件开发培训","评分":8,"原因":"语法正确,意义明确"}],根据用户输入的关键词或者关键词组,按照格式输出判定结果.
"""
KEYWORD_FILE_PATH = Path(__file__).parent.parent.joinpath('data/keyword1.txt')
LOCAL_RSP_FILE_PATH = Path(__file__).parent.parent.joinpath('data/rsp_local.txt')
FAIL_RSP_FILE_PATH = Path(__file__).parent.parent.joinpath('data/rsp_fail.txt')
AI_MODEL_MAP = {
"MODEL_ID_DEEPSEEK_V3" : 'ep-20250407223552-sb9r2',
"MODEL_ID_DEEPSEEK_R1" : 'ep-20250208112736-r5hxt',
"MODEL_ID_DOUBAO_PRO_v" : 'ep-20250411143831-q62g9',
"MODEL_ID_DOUBAO_PRO" : 'ep-20250411162009-bmn68',
"MODEL_ID_DOUBAO_PRO_256":'ep-20250411162253-4b2g4'
}
MAX_CONCURRENT_TASKS = 20 # Control total concurrent tasks (like a pool size)

MODEL_SELECT = 'DOUBAO_PRO_256'

if  not AI_MODEL_MAP.get(f'MODEL_ID_{MODEL_SELECT}'):
    print(f'{MODEL_SELECT} is not in AI_MODEL_MAP,使用默认的DEEPSEEK_V3')
    MODEL_SELECT = 'DEEPSEEK_V3'
MODEL_ID = AI_MODEL_MAP.get(f'MODEL_ID_{MODEL_SELECT}')


# --- Main Asynchronous Function ---
async def async_main(batch_size: int = 100):
    """
    Main asynchronous function to orchestrate the keyword processing.
    """
    file_info = FileInfo(local_rsp_file_path=LOCAL_RSP_FILE_PATH,
                         local_format_fail_file_path=FAIL_RSP_FILE_PATH)
    beg_time = time.time()

    # --- Setup (Keep synchronous for simplicity unless proven bottleneck) ---
    client = CURD()
    print("Reading keywords...")
    keywords = get_keyword(KEYWORD_FILE_PATH)
    print(f"Read {len(keywords)} keywords.")
    print("Querying existing keywords from DB...")
    db_item = client.query_keyword_in_keyword_seo_score_with_reason()
    print(f"Found {len(db_item)} existing keywords in DB.")
    keywords = preserve_order_deduplicate(keywords)
    keywords_to_process = [item for item in keywords if item not in db_item]
    print(f"Keywords to process after deduplication and DB check: {len(keywords_to_process)}")
    success_save = 0
    failed_save = 0
    # --- End Setup ---


    if not keywords_to_process:
        print("No new keywords to process.")
        return

    # --- Create Queue and Start Saver Process ---
    # Use Manager().Queue() if running in more complex scenarios (like Jupyter),
    # but standard Queue is fine here.
    results_queue = multiprocessing.Queue()
    print("Starting saver process...")
    saver_p = multiprocessing.Process(
        target=saver_process_func,
        args=(results_queue, LOCAL_RSP_FILE_PATH, FAIL_RSP_FILE_PATH,MODEL_SELECT),
        daemon=True # Set as daemon if you want it to exit automatically if main process crashes
                    # If False (default), you MUST ensure it terminates via the sentinel
    )
    saver_p.start()
    # --- Saver Process Started ---
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    tasks = []

    print(f'---------- Starting async requests (Max concurrency: {MAX_CONCURRENT_TASKS}) ----------')
    for i in range(0, len(keywords_to_process), batch_size):
        batch_keywords = keywords_to_process[i:i + batch_size]
        if not batch_keywords:
            continue
        task = async_get_ai_rsp(
            system_role_content=SYSTEM_ROLE_CONTENT,
            keywords=batch_keywords,
            model_id=MODEL_ID,
            semaphore = semaphore,
        )
        tasks.append(task)
    # Wait for all created tasks to complete
    print(f"Created {len(tasks)} processing tasks. Waiting for completion...")
    over_task = 0
    total_task = len(tasks)
    for completed in asyncio.as_completed(tasks):
        try:
            result = await completed # Get AI result
            if result: # Basic check if result is valid
                 results_queue.put(result) # Put result onto the queue for the saver process
                 # print(f"AI Task {ai_tasks_completed + 1}/{ai_tasks_submitted} completed, result sent to saver.")
            else:
                 print(f"AI Task {over_task + 1}/{total_task} completed but returned empty/invalid result.")

        except Exception as e:
             print(f"AI Task {over_task + 1}/{total_task} failed with exception: {e}")
        finally:
            over_task += 1
            print(f"\rProgress: AI tasks completed: {over_task}/{total_task}", end="")

    # --- Signal Saver Process to Terminate ---
    print("\nSending termination signal to saver process...")
    results_queue.put(TERMINATION_SENTINEL)

    # --- Wait for Saver Process to Finish ---
    print("Waiting for saver process to finish saving remaining items...")
    saver_p.join() # Wait until the saver process exits
    print("Saver process has finished.")
    
    total_time = time.time() - beg_time
    
    
    print(f'---------- Processing Finished ----------')
    print(f'Total Batches: {len(tasks)}')
    print(f'Total time: {total_time:.2f} seconds')

    # Note: The original code's print statement about insertion success is now inside process_batch
    # as each task completes independently.

# --- Script Entry Point ---
if __name__ == '__main__':
    # Run the main asynchronous function
    # For Python 3.7+
    #补录之前的错误 如果存在
    update_rsp_fail_txt_to_score_with_reason(ai_model=MODEL_SELECT)
    asyncio.run(async_main(batch_size=100)) # Adjust batch_size if needed
