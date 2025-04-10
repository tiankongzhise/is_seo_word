from .get_ai_rsp_by_keyword_list import get_ai_rsp
from .utils import get_keyword
from .datebase.curd import CURD
from pathlib import Path
from tkzs_bd_db_tool import get_session
from .datebase.models import KeywordBuyScore
import time



def main(batch_size=1000):
    start_time = time.time()
    file_path = Path(__file__).parent.parent.parent.joinpath("data", "keyword1.txt")
    fail_save_path = Path(__file__).parent.parent.parent.joinpath("data", "fail_keyword_async.txt")
    
    # 初始化数据库客户端
    client = CURD()
    
    # 获取关键词列表
    local_keyword_list = get_keyword(file_path)
    
    
    with get_session() as session:
        rsp = session.query(KeywordBuyScore).all()
        db_keyword_list = [item.keyword for item in rsp]
    keywords_list = [keyword for keyword in local_keyword_list if keyword not in db_keyword_list]
    total = len(keywords_list)
    print(f'一共有{total}个关键词,需要打分')

    for i in range(0, len(keywords_list), batch_size):
        batch = keywords_list[i:i+batch_size]

        rsp = get_ai_rsp(batch)
        if rsp.get('status','fail') == 'success':
            insert_time = time.time()
            client.bulck_insert_keyword_buy_score(rsp['data'])
            print(f"第{i}到{i+batch_size}关键词插入数据库成功,耗时{insert_time - start_time}秒")
        else:
            with open(fail_save_path, "a", encoding="utf-8") as f:
                f.write(rsp['data'] + "\n")
            print(f"第{i}到{i+batch_size}关键词打分失败,已保存到{fail_save_path}")
    end_time = time.time()
    print(f"共耗时{end_time - start_time}秒")
    