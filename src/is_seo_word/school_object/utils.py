from ..utils import get_keyword,preserve_order_deduplicate
from ..datebase.curd import CURD
from pathlib import Path

def get_keywords_to_process(file_path:Path,client:CURD):
    keywords = get_keyword(file_path)
    print(f"Read {len(keywords)} keywords.")
    keywords = preserve_order_deduplicate(keywords)
    print("Querying existing keywords from DB...")
    db_data = client.query_keyword_in_keyword_with_region()
    print(f"Found {len(db_data)} existing keywords in DB.")
    keywords_to_process = [item for item in keywords if item.lower() not in db_data]
    print(f"Keywords to process after deduplication and DB check: {len(keywords_to_process)}")
    # print(f'keywords_to_process:{keywords_to_process}')
    return keywords_to_process

def find_files(root_path, extensions):
    """
    遍历目录及其子目录，返回所有匹配扩展名的文件路径列表
    :param root_path: 根目录路径
    :param extensions: 目标扩展名列表，如 [".docx", ".doc", ".pdf"]
    :return: 匹配的文件路径列表
    """
    root_dir = Path(root_path)
    matched_files = []
    for ext in extensions:
        matched_files.extend(root_dir.glob(f"**/*{ext}"))
    return matched_files