
from pathlib import Path
import time


from src.is_seo_word.datebase.curd import CURD
from src.is_seo_word.models import FileInfo
from src.is_seo_word.get_ai_rsp_v3 import get_ai_rsp
from src.is_seo_word.utils import get_keyword
from src.is_seo_word.utils import preserve_order_deduplicate,save_rsp_v3_result



def test_get_ai_rsp_v3(batch_size:int=100):
    system_role_content = r"""你是一个SEM关键词筛选系统,对用户输入的一个或者一组关键词的每关键词进行判别是否是一个seo生造词,判断的维度为是否出现不合理重复,语法不符合人类语言习惯,逻辑混乱等.评分从0-100,越接近100表示越可能是SEO生造词.不是人类用户的搜索习惯,
    输出结果格式为一个标准的json组成的List 格式为[{"关键词":XXXX,"评分":xxxx,"原因":xxxx}],举例用户输入为网络信息安全培训培训,网络安全+渗透+培训,网络网络工程培训机构,网络工程培训培训,网络网络运维,Java培训,软件开发培训 则输出结果为
    [{"关键词":"网络信息安全培训培训","评分":80,"原因":"[培训]连续重复,不符合常见语法"},
    {"关键词":"网络安全+渗透+培训","评分":93,"原因":"堆叠关键词,使用的符号[+],并不是正常搜索常见符号,反而是搜索优化常用符号"},
    {"关键词":"网络网络工程培训机构","评分":92,"原因":"[网络]连续重复,且不符合语法,逻辑意义不明"},
    {"关键词":"网络工程培训培训","评分":85,"原因":"[培训]连续重复,语法不符合人类语言习惯"},
    {"关键词":"编程 开发培训学校","评分":63,"原因":"出现[空格],关键词组合稍显生硬"},
    {"关键词":"计算机 开发 学习","评分":92,"原因":"[空格]连续出现,不符合常见输入习惯"},
    {"关键词":"网络网络运维","评分":88,"原因":"[网络]出现重复,分析后不符合逻辑,不具备明确搜索意图"},
    {"关键词":"的软件开发培训机构","评分":99,"原因":"[的],出现位置不符合语法,且后继一个明确的培训类关键词,符合seo优化特征"},
    {"关键词":"软件开发的培训机构","评分":64,"原因":"[的],出现位置不太符合人类用词习惯,且连接两个独立的关键词,比较符合seo特征"},
    {"关键词":"软件开发培训的机构","评分":35,"原因":"[的]出现位置比较符合用词习惯,且语法正确,意义比较明确"},
    {"关键词":"培训软件开发中心","评分":90,"原因":"关键词堆砌,不符合人类搜索习惯"},
    {"关键词":"培训中心软件开发","评分":93,"原因":"关键词堆砌,不符合人类搜索习惯"},
    {"关键词":"Java培训","评分":10,"原因":"语法正确,意义明确"},
    {"关键词":"软件开发培训","评分":8,"原因":"语法正确,意义明确"}],根据用户输入的关键词或者关键词组,按照格式输出判定结果.
    """
    keyword_file_path = Path(__file__).parent.parent.joinpath('data/keyword1.txt')
    local_rsp_file_path = Path(__file__).parent.parent.joinpath('data/rsp_local.txt')
    fail_rsp_file_path = Path(__file__).parent.parent.joinpath('data/rsp_fail.txt')
    file_info = FileInfo(local_rsp_file_path=local_rsp_file_path,
                         local_format_fail_file_path=fail_rsp_file_path)
    beg_time = time.time()
    client = CURD()
    keywords = get_keyword(keyword_file_path)
    db_item = client.query_keyword_in_keyword_seo_score_with_reason()
    keywords = preserve_order_deduplicate(keywords)
    keywords = [item for item in keywords if item not in db_item]
    
    model_id = 'ep-20250407223552-sb9r2'
    print(f'---------- 开始正式请求 ------------')
    for i in range(0,len(keywords),batch_size):
        batch_keywords = keywords[i:i+batch_size]
        rsp = get_ai_rsp(system_role_content=system_role_content,
                        keywords=batch_keywords,
                        stream=True,
                        model_id=model_id)
        save_rsp_v3_result(rsp=rsp,client=client,file_info=file_info)
        print(f'第{i}到{i+batch_size}关键词插入数据库成功')

    total_time = time.time() - beg_time
    print(f'共耗时{total_time}秒')

if __name__ == '__main__':
    test_get_ai_rsp_v3()
