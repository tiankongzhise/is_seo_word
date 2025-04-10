import pandas as pd
import json
import re

from pathlib import Path
from decimal import Decimal, getcontext

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