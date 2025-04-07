import os
from openai import OpenAI
from dotenv import load_dotenv
from .models import KeywordScore
from decimal import Decimal, getcontext
# 设置全局精度为 2 位小数
getcontext().prec = 4  # 包含整数位 + 小数位（如 0.12 需要 3 位精度）
load_dotenv()

def get_ai_rsp(keyword):
    client = OpenAI(
        api_key = os.environ.get("ARK_API_KEY"),
        base_url = "https://ark.cn-beijing.volces.com/api/v3",
    )

    # Non-streaming:
    # print("----- standard request -----")
    completion = client.chat.completions.create(
        model = "ep-20250407223552-sb9r2",  # your model endpoint ID
        messages = [
            {"role": "system", "content": "你是一个关键词判别器,对用户输入的关键词进行判别,判断是正常的用户搜索需求,还是SEO工作者生造的无意义拼凑词.值为0-1,越接近1标识越有可能是生造无意义词,越接近0表示越可能是用户的正常搜索习惯,结果只需要回答一个0-1之间的小数,不需要其他内容"},
            {"role": "user", "content": "培训网络安全"},
        ],
    )
    rsp = completion.choices[0].message.content
    print(f'{keyword}:{rsp}')
    return KeywordScore(keyword=keyword,score=Decimal(rsp))
   