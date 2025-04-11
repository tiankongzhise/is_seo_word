from .utils import load_toml, get_keyword

from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

import os
import time



load_dotenv()



toml_config = load_toml('ai_model_test.toml')

def get_ai_rsp(
    system_role_content: str | None = None,
    keywords: str | list | None = None,
    stream: bool | None = None,
    model_id: str | None = None,
    **kwargs,
):
    # 获取配置信息
    if system_role_content is None:
        system_role_content = toml_config.get("SYSTEM_ROLE_CONTENT")
        if system_role_content is None:
            raise ValueError("system_role_content is None")
    if keywords is None:
        keywords_file_name = toml_config.get("KEYWORDS_FILE_NAME")
        if keywords_file_name is None:
            raise ValueError("keywords is None")
        keywords_file_dir = toml_config.get("KEYWORDS_FILE_DIR")
        if keywords_file_dir is None:
            keywords_file_dir = Path(__file__).parent.parent.parent / "data"
        keywords = get_keyword(keywords_file_dir / keywords_file_name)
    if stream is None:
        stream = (
            toml_config.get("STREAM")
            if toml_config.get("STREAM") is not None
            else False
        )
    if model_id is None:
        model_id = toml_config.get("MODEL_ID")
        if model_id is None:
            raise ValueError("model_id is None")

    # 创建OpenAI客户端
    client = OpenAI(
        api_key=os.environ.get("ARK_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )
    if isinstance(keywords, str):
        keywords = [keywords]
    elif isinstance(keywords, list):
        pass
    else:
        raise TypeError("keyword must be str or list")

    # Non-streaming:
    print("----- standard request -----")
    start_time = time.time()
    completion = client.chat.completions.create(
        model=model_id,  # your model endpoint ID
        messages=[
            {"role": "system", "content": system_role_content},
            {"role": "user", "content": "\n".join(keywords)},
        ],
        stream=stream,
    )
    if stream:
        rsp = ""
        for chunk in completion:
            rsp += chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="")
    else:
        rsp = completion.choices[0].message.content
    print(f"本轮数据已返回,耗时间:{time.time() - start_time}")
    return [rsp]



if __name__ == "__main__":
    print(get_ai_rsp())
