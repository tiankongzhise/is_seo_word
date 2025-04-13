import asyncio
import time
import multiprocessing # Import multiprocessing

from pathlib import Path


# Assuming these imports exist and work as in the original code
from src.is_seo_word.datebase.curd import CURD
from src.is_seo_word.models import FileInfo
from src.is_seo_word.get_ai_rsp_v3 import async_get_ai_rsp # Assuming this can be awaited or adapted
from src.is_seo_word.utils import (get_abs_file_path,
                                   saver_process_func,
                                   TERMINATION_SENTINEL,
                                   update_rsp_fail_txt_to_score_with_reason,
                                   load_toml,
                                   get_abs_file_path)
from .utils import get_keywords_to_process
from .core import AiAgent
from .save import save_rsp_result

# --- Main Asynchronous Function ---
async def async_main(batch_size: int = 100):
    """
    Main asynchronous function to orchestrate the keyword processing.
    """
    config = load_toml('config.toml')
    local_rsp_file_path=get_abs_file_path(config['LOCAL_RSP_FILE_PATH'])
    local_format_fail_file_path=get_abs_file_path(config['FAIL_RSP_FILE_PATH'])
    ai_model = config['AI_MODEL']
    max_concurrent_tasks = config['MAX_CONCURRENT_TASKS']

    beg_time = time.time()

    # --- Setup (Keep synchronous for simplicity unless proven bottleneck) ---
    client = CURD()
    keywords_file_path = get_abs_file_path(config['KEYWORDS_FILE_NAME'])
    keywords_to_process = get_keywords_to_process(keywords_file_path,client)
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
        args=(results_queue, local_rsp_file_path, local_format_fail_file_path,ai_model,save_rsp_result),
        daemon=True # Set as daemon if you want it to exit automatically if main process crashes
                    # If False (default), you MUST ensure it terminates via the sentinel
    )
    saver_p.start()
    # --- Saver Process Started ---
    
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    tasks = []

    print(f'---------- Starting async requests (Max concurrency: {max_concurrent_tasks}) ----------')
    agent = AiAgent()
    agent.set_agent_config(system_role_content=config['SYSTEM_ROLE_CONTENT'],
                           stream=False,
                           model_id=config['MODEL_ID'],
                           semaphore=semaphore)


    for i in range(0, len(keywords_to_process), batch_size):
        batch_keywords = keywords_to_process[i:i + batch_size]
        if not batch_keywords:
            continue
        task = agent.async_get_ai_rsp(batch_keywords)
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


