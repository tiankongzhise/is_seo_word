from .get_ai_rsp import get_ai_rsp
from .utils import get_keyword
from .datebase.curd import CURD
from pathlib import Path
from tqdm import tqdm




def main():
    file_path = Path(__file__).parent.parent.parent.joinpath("data","keyword.txt")
    fail_save_path = Path(__file__).parent.parent.parent.joinpath("data","fail_keyword.txt")
    keywords_list = get_keyword(file_path)
    rsp = []
    client = CURD()
    # 批量处理缓冲区
    buffer = []
    batch_size = 5
    count = 0
    total = len(keywords_list)
    fail_keywords = []
    for index, keyword in enumerate(keywords_list, 1):
        # 获取AI响应
        try:
            ai_response = get_ai_rsp(keyword)
        except Exception as e:
            print(f"获取AI响应失败：{e}")
            fail_keywords.append(keyword)
            continue
        rsp.append(ai_response)
        buffer.append(ai_response)
        
        # 达到批次数量或处理完所有元素时提交
        if index % batch_size == 0 or index == len(keywords_list):
            client.bluck_insert_keyword_seo_score(buffer)
            buffer = []  # 清空缓冲区
            print(f"已处理{index}个关键词")
        count += 1
        tqdm.write(f"{count}/{total}")
    if fail_keywords:
        with open(fail_save_path, "w", encoding="utf-8") as f:
            for keyword in fail_keywords:
                f.write(keyword + "\n")
    return rsp
