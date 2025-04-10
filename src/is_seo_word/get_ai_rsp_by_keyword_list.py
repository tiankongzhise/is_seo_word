import os
from openai import OpenAI
from dotenv import load_dotenv
from .models import KeywordScore
from decimal import Decimal, getcontext
from .utils import format_rsp_to_dict
import time
# 设置全局精度为 2 位小数
getcontext().prec = 4  # 包含整数位 + 小数位（如 0.12 需要 3 位精度）
load_dotenv()

def get_ai_rsp(keyword:str|list):
    client = OpenAI(
        api_key = os.environ.get("ARK_API_KEY"),
        base_url = "https://ark.cn-beijing.volces.com/api/v3",
    )
    if isinstance(keyword,str):
        keyword = [keyword]
    elif isinstance(keyword,list):
        pass
    else:
        raise TypeError('keyword must be str or list')

    # Non-streaming:
    print("----- standard request -----")
    start_time = time.time()
    completion = client.chat.completions.create(
        model = "ep-20250208112736-r5hxt",  # your model endpoint ID
        messages = [
            {"role": "system", "content": "你是一个SEM关键词推荐系统,对用户输入的一个或者一组关键词的每关键词进行判别,结合词性,词根,词面意图,决策阶段,是否符合自然语言语法,判断用户的购买意向,给出建议值.值为0-1,越接近1标识越有可能成交,越接近0表示成交越困难,结果输出为标准json格式,key为关键词,value对应的评分,评分是一个0-1之间的小数组,不需要其他内容"},
            {"role": "user", "content": '\n'.join(keyword)},
        ],
    )
    rsp = completion.choices[0].message.content
    print(f'本轮数据已返回,耗时间:{time.time()-start_time}')
    try:
        rsp = format_rsp_to_dict(rsp)
        return {'status':'success','data':[KeywordScore(keyword=keyword,score=Decimal(score)) for keyword,score in rsp.items()]}
    except Exception as e:
        print(e)
        print([rsp])
        return {'status':'fail','data':rsp,'err_msg':str(e)}
   