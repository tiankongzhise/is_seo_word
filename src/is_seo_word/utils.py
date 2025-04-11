import pandas as pd
import json
import re
import tomllib
import multiprocessing # Import multiprocessing
import sys
import os

from pathlib import Path
from decimal import Decimal, getcontext
from typing import List,Iterator


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

def format_rsp(rsp:str,**kwargs):
    match kwargs.get('ai_model'):
        case "DEEPSEEK_V3":
            pattern = r'```json\n([\s\S]*?)```'
            result = re.findall(pattern, rsp)[0].strip()
            return result
        case 'DEEPSEEK_R1':
            pattern = r'```json\n([\s\S]*?)```'
            result = re.findall(pattern, rsp)[0].strip()
            return result
        case 'DOUBAO_PRO':
            return rsp
        case 'DOUBAO_PRO_V':
            return rsp
        case 'DOUBAO_PRO_256':
            return rsp
        case _:
            return rsp
            
        

def formated_rsp_to_dict_list(json_str:str)->list[dict]|None:
    # 修复 JSON 字符串中的异常空格（处理"评 分"的格式问题）
    fixed_json = json_str.replace('"评 分":', '"评分":')
    try:
        result = json.loads(fixed_json)
        return result
    except json.JSONDecodeError as e:
        print(f"解析错误：{e.msg}，错误位置：{e.pos}")
        print(f'\n[{json_str}]\n')
        return None

def preserve_order_deduplicate(lst: List[str]) -> List[str]:
    """保序去重函数（兼容Python 3.6+）"""

    seen = set()

    return [x for x in lst if not (x in seen or seen.add(x))]

def save_rsp_v3_result(rsp:str,client:CURD,file_info:FileInfo,ai_model:str):
    try:
        local_rsp_file_path = file_info.local_rsp_file_path
        fail_rsp_file_path = file_info.local_format_fail_file_path
        
        with open(local_rsp_file_path,'a',encoding='utf-8') as f:
            f.write(rsp)
        json_str = format_rsp(rsp,ai_model=ai_model)
        formated_item = formated_rsp_to_dict_list(json_str)
        if formated_item is None:
            with open(fail_rsp_file_path,'a',encoding='utf-8') as f:
                f.write(rsp)
            return None
        temp_list =[]
        try:
            for item in formated_item:
                temp_list.append(KeywordScoreWithReason(keyword=item['关键词'],
                                                        score=item['评分'],
                                                        reason=item['原因'],
                                                        ai_model=ai_model)
                                                        )
            client.bulck_insert_keyword_seo_score_with_reason(temp_list)
        except Exception as e:
            print(f'数据库写入失败,原因为{e},rsp为{rsp}')
            with open(fail_rsp_file_path,'a',encoding='utf-8') as f:
                f.write(rsp)
            return False
        return True
    except Exception as e:
        print(e)
        return False

TERMINATION_SENTINEL = None # Signal for the saver process to stop

# --- Saver Process Function ---
def saver_process_func(results_queue: multiprocessing.Queue, local_rsp_path: Path, fail_rsp_path: Path,ai_model:str):
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
                save_successful = save_rsp_v3_result(rsp=result, client=client, file_info=file_info,ai_model=ai_model)
                if save_successful:
                    saved_count +=1
                    print(f"[Saver Process {multiprocessing.current_process().pid}] Saved result successfully.")
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


def _walk_to_root(path: str) -> Iterator[str]:
    """
    Yield directories starting from the given directory up to the root
    """
    if not os.path.exists(path):
        raise IOError("Starting path not found")

    if os.path.isfile(path):
        path = os.path.dirname(path)

    last_dir = None
    current_dir = os.path.abspath(path)
    while last_dir != current_dir:
        yield current_dir
        parent_dir = os.path.abspath(os.path.join(current_dir, os.path.pardir))
        last_dir, current_dir = current_dir, parent_dir

def find_toml(
    filename: str = ".toml",
    raise_error_if_not_found: bool = False,
    usecwd: bool = False,
) -> str:
    """
    Search in increasingly higher folders for the given file

    Returns path to the file if found, or an empty string otherwise
    """

    def _is_interactive():
        """Decide whether this is running in a REPL or IPython notebook"""
        try:
            main = __import__("__main__", None, None, fromlist=["__file__"])
        except ModuleNotFoundError:
            return False
        return not hasattr(main, "__file__")

    def _is_debugger():
        return sys.gettrace() is not None

    if usecwd or _is_interactive() or _is_debugger() or getattr(sys, "frozen", False):
        # Should work without __file__, e.g. in REPL or IPython notebook.
        path = os.getcwd()
    else:
        # will work for .py files
        frame = sys._getframe()
        current_file = __file__

        while frame.f_code.co_filename == current_file or not os.path.exists(
            frame.f_code.co_filename
        ):
            assert frame.f_back is not None
            frame = frame.f_back
        frame_filename = frame.f_code.co_filename
        path = os.path.dirname(os.path.abspath(frame_filename))

    for dirname in _walk_to_root(path):
        check_path = os.path.join(dirname, filename)
        if os.path.isfile(check_path):
            return check_path

    if raise_error_if_not_found:
        raise IOError("File not found")

    return ""



def load_toml(toml_file_name:str|None = None,toml_file_path:str|Path|None = None):
    if toml_file_name is None:
        toml_file_name = 'pyproject.toml'
    if toml_file_path is None:
        toml_file_path = find_toml(toml_file_name, raise_error_if_not_found=True)
    try:
        with open(toml_file_path, 'rb') as toml_file:
            config = tomllib.load(toml_file)
        return config
    except FileNotFoundError:
        print("config.toml file not found.")
        return {}
    except Exception as e:
        print(f"Error loading config.toml: {e}")
        return {}

def load_fail_txt(fail_txt_path:str|Path|None = None) -> List[dict] | None:
    if fail_txt_path is None:
        fail_txt_path = Path(__file__).parent.parent.parent.joinpath("data","rsp_fail.txt")
    if not fail_txt_path.is_file():
        print(f'rsp_fail.txt文件不存在,文件路径{fail_txt_path}')
        return None
    
    try:
        with open(fail_txt_path, 'r',encoding='utf-8') as fail_txt:
            fail_keywords = fail_txt.readlines()
        return json.loads(''.join(fail_keywords))
    except FileNotFoundError:
        print("rsp_fail.txt file not found.")
    except Exception as e:
        print(f"Error loading rsp_fail.txt: {e}")

def update_rsp_fail_txt_to_score_with_reason(fail_txt_path:str|Path|None = None,**kwargs):
    client = CURD()
    if fail_txt_path is None:
        fail_txt_path = Path(__file__).parent.parent.parent.joinpath("data","rsp_fail.txt")
    fail_item = load_fail_txt(fail_txt_path=fail_txt_path)
    temp_list =[]
    try:
        if not fail_item:
            print('rsp_fail.txt为空')
            return 
        if kwargs.get('ai_model'):
            ai_model = kwargs.get('ai_model')
        else:
            ai_model = f'关键词:{fail_item[0]['关键词']}-需要人工修改模型'
        for item in fail_item:
            temp_list.append(KeywordScoreWithReason(keyword=item['关键词'],
                                                    score=item['评分'],
                                                    reason=item['原因'],
                                                    ai_model=ai_model)
                                                    )
        client.bulck_insert_keyword_seo_score_with_reason(temp_list)
        print(f'补写rsp_fail.txt成功,共写入{len(temp_list)}条数据')
        try:
            fail_txt_path.unlink()
            print('rsp_fail.txt文件删除成功')
        except Exception as e:
            print(f'rsp_fail.txt文件删除失败,原因为{e}')
    except Exception as e:
        print(f'数据库写入失败,原因为{e}')
