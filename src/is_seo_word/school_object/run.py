from ..utils import load_toml,get_abs_file_path
from .utils import find_files
from .core import AiAgent

import asyncio


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
    docx_files = find_files(root_dir, [".docx",'.doc','.pdf'])
    print(f"Found {docx_files} ")
    for docx_file in docx_files:
        file_id = agent.upload_file(docx_file)
        agent.assistant_agent(file_id)
        