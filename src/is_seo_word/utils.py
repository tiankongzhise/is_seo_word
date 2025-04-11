import pandas as pd
import json
import re
import multiprocessing # Import multiprocessing

from pathlib import Path
from decimal import Decimal, getcontext
from typing import List


from .models import FileInfo,KeywordScoreWithReason
from .datebase.curd import CURD


def get_keyword(file_path:Path):
    if file_path.is_file():
        df = pd.read_csv(file_path,sep='\t',header=None)
        return df[0].tolist()
    else:
        return []



def format_rsp_to_dict(rsp:str):
    # 使用正则表达式提取 ```包裹的JSON内容
    match = re.search(r'```json\n(.*?)\n```', rsp, re.DOTALL)
    json_dict = None
    if match:
        # 提取大括号内容并去除换行符
        json_content = match.group(1)
        compact_json = json_content.replace('\n', '')
        json_dict = json.loads(compact_json)
    if json_dict:
        return json_dict

def format_rsp(rsp:str):
    pattern = r'```json\n([\s\S]*?)```'
    result = re.findall(pattern, rsp)[0].strip()
    return result

def formated_rsp_to_dict_list(json_str:str)->list[dict]|None:
    # 修复 JSON 字符串中的异常空格（处理"评 分"的格式问题）
    fixed_json = json_str.replace('"评 分":', '"评分":')
    try:
        result = json.loads(fixed_json)
        return result
    except json.JSONDecodeError as e:
        print(f"解析错误：{e.msg}，错误位置：{e.pos}")
        return None

def preserve_order_deduplicate(lst: List[str]) -> List[str]:
    """保序去重函数（兼容Python 3.6+）"""

    seen = set()

    return [x for x in lst if not (x in seen or seen.add(x))]

def save_rsp_v3_result(rsp:str,client:CURD,file_info:FileInfo):
    try:
        local_rsp_file_path = file_info.local_rsp_file_path
        fail_rsp_file_path = file_info.local_format_fail_file_path
        
        with open(local_rsp_file_path,'a',encoding='utf-8') as f:
            f.write(rsp)
        json_str = format_rsp(rsp)
        formated_item = formated_rsp_to_dict_list(json_str)
        if formated_item is None:
            with open(fail_rsp_file_path,'a',encoding='utf-8') as f:
                f.write(rsp)
            return None
        temp_list =[]
        for item in formated_item:
            temp_list.append(KeywordScoreWithReason(keyword=item['关键词'],
                                                    score=item['评分'],
                                                    reason=item['原因']))
        client.bulck_insert_keyword_seo_score_with_reason(temp_list)
        return True
    except Exception as e:
        print(e)
        return False

TERMINATION_SENTINEL = None # Signal for the saver process to stop

# --- Saver Process Function ---
def saver_process_func(results_queue: multiprocessing.Queue, local_rsp_path: Path, fail_rsp_path: Path):
    """
    This function runs in a separate process.
    It listens on the queue for results and saves them using the synchronous function.
    """
    print(f"[Saver Process {multiprocessing.current_process().pid}] Initializing...")
    # Each process needs its own DB client and FileInfo
    try:
        client = CURD()
        file_info = FileInfo(local_rsp_file_path=local_rsp_path,
                             local_format_fail_file_path=fail_rsp_path)
        print(f"[Saver Process {multiprocessing.current_process().pid}] Ready to save results.")
        saved_count = 0
        error_count = 0
        while True:
            # Get result from the queue (blocks until item is available)
            result = results_queue.get()

            # Check for termination signal
            if result is TERMINATION_SENTINEL:
                print(f"[Saver Process {multiprocessing.current_process().pid}] Termination signal received. Exiting.")
                break

            # Process the received result
            try:
                # Use the original synchronous save function
                save_successful = save_rsp_v3_result(rsp=result, client=client, file_info=file_info)
                if save_successful:
                    saved_count +=1
                    # print(f"[Saver Process {multiprocessing.current_process().pid}] Saved result successfully.")
                else:
                    error_count +=1
                    print(f"[Saver Process {multiprocessing.current_process().pid}] Failed to save result (save_rsp_v3_result returned False/error).")
            except Exception as e:
                error_count += 1
                print(f"[Saver Process {multiprocessing.current_process().pid}] EXCEPTION while saving result: {e}")
                # Depending on save_rsp_v3_result, decide if you need more robust error handling here

    except Exception as e:
         print(f"[Saver Process {multiprocessing.current_process().pid}] FATAL INITIALIZATION ERROR: {e}")
    finally:
        # Optional: Add cleanup here if CURD client needs explicit closing
        # client.close()
        print(f"[Saver Process {multiprocessing.current_process().pid}] Final saved count: {saved_count}, Errors: {error_count}")
        pass # Process terminates
