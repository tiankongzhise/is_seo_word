from ..utils import load_toml,get_abs_file_path,format_rsp,formated_rsp_to_dict_list
from .utils import find_files
from .core import AiAgent
from .upload_file import read_file
from ..models import SchoolObject
from ..datebase.curd import CURD
from ..datebase.models import SchoolObjectTable
import asyncio
from pathlib import Path


# --- Script Entry Point ---
def run(batch_size: int|None = None):
    # Run the main asynchronous function
    # For Python 3.7+
    #补录之前的错误 如果存在
    agent = AiAgent()
    config = load_toml('config.toml')
    fail_file_path = get_abs_file_path(config['UPLOAD_DIR'])
    """遍历目录及其子目录，返回所有 .docx 文件的路径列表"""
    root_dir = fail_file_path  # 转换为 Path 对象
    files:list[Path] = find_files(root_dir, [".docx",'.doc','.pdf'])
    print(f"Found {files} ")
    db_client = CURD()
    db_school_info =db_client.query_keyword_in_school_object()
    for file_path in files:
        file_str = read_file(file_path)
        if not file_str:
            print(f"{file_path.stem}为空文件,跳过")
            continue
        if file_path.stem in db_school_info:
            print(f"{file_path.stem}已经存在数据库中,跳过")
            continue
        print(f"{file_path.stem}开始处理")
        rsp = agent.get_ai_rsp(file_str)
        try:
            rsp = format_rsp(rsp[0],ai_model = config['AI_MODEL'])
            print(f"{file_path.stem}格式化rsp成功,{rsp}")
        except Exception as e:
            print(f"{file_path.stem}格式化rsp出错,Error: {e}")
            continue
        
        try:
            rsp = formated_rsp_to_dict_list(rsp)
            print(f"{file_path.stem}格式化rsp_to_dict成功,{rsp}")
        except Exception as e:
            print(f"{file_path.stem}格式化rsp_to_dict出错,Error: {e}")
            continue
        
        try:
            school_object = [SchoolObject(**{
                'school_name':rsp_item['学校名称'],
                'school_type':rsp_item['学校性质'],
                'school_level':rsp_item['办学层次'],
                'school_address':rsp_item['办学地点'],
                'is_sfx_school':rsp_item['示范性院校'],
                'is_gz_school':rsp_item['骨干院校'],
                'is_zy_school':rsp_item['卓越院校'],
                'is_cy_school':rsp_item['楚怡高水平院校'],
                'major':rsp_item['优势专业']
            }) for rsp_item in rsp]
        except Exception as e:
            print(f"{file_path.stem}格式化rsp_to_SchoolObject出错,Error: {e}")
            continue
        
        try:
            db_client.bluck_insert_school_object(school_object)
            print(f"{file_path.stem}插入数据库成功")
        except Exception as e:
            print(f"{file_path.stem}插入数据库出错,Error: {e}")
            continue







        