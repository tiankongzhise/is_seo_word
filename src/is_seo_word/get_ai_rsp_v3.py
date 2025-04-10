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

def get_ai_rsp(system_role_content:str,keywords:str|list,stream:bool=False,model_id:str='ep-20250208112736-r5hxt'):
    client = OpenAI(
        api_key = os.environ.get("ARK_API_KEY"),
        base_url = "https://ark.cn-beijing.volces.com/api/v3",
    )
    if isinstance(keywords,str):
        keyword = [keywords]
    elif isinstance(keywords,list):
        pass
    else:
        raise TypeError('keyword must be str or list')

    # Non-streaming:
    print("----- standard request -----")
    start_time = time.time()
    completion = client.chat.completions.create(
        model = model_id,  # your model endpoint ID
        messages = [
            {"role": "system", "content": system_role_content},
            {"role": "user", "content": '\n'.join(keywords)},
        ],
        stream=stream
    )
    if stream:
        rsp = ''
        for chunk in completion:
            rsp += chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content,end='')
    else:
        rsp = completion.choices[0].message.content
    print(f'本轮数据已返回,耗时间:{time.time()-start_time}')
    return rsp