from ..utils import load_toml, get_keyword,get_abs_file_path

from contextlib import nullcontext
from openai import OpenAI,AsyncOpenAI
from dotenv import load_dotenv
from pathlib import Path

import os
import time
import asyncio 



load_dotenv()


class AiAgent(object):
    def __init__(self,agent_name:str = 'default'):
        self.system_role_content:str = None
        self.keywords:str|list|None = None
        self.stream:bool = None
        self.model_id:str = None
        self.kwargs:dict = None
        self.agent_name:str = agent_name
        self.toml_config = load_toml('config.toml')
        self.set_agent_config()
    
    def set_agent_config(self,system_role_content:str|None = None,
                         keywords:str|list| None = None,
                         stream:bool| None = None,
                         model_id:str| None = None,
                         **kwargs):

        # 获取配置信息
        if system_role_content is None:
            self.system_role_content = self.toml_config.get("SYSTEM_ROLE_CONTENT")
            if self.system_role_content is None:
                raise ValueError("system_role_content is None")
        else:
            self.system_role_content = system_role_content


        if keywords is None:
            keywords_file_name = self.toml_config.get("KEYWORDS_FILE_NAME")
            if keywords_file_name is None:
                raise ValueError("keywords is None")
            self.keywords = get_keyword(get_abs_file_path(keywords_file_name))
        else:
            self.keywords = keywords
        if stream is None:
            self.stream = (
                self.toml_config.get("STREAM")
                if self.toml_config.get("STREAM") is not None
                else False
            )
        else:
            self.stream = stream
        if model_id is None:
            self.model_id = self.toml_config.get("MODEL_ID")
            if self.model_id is None:
                raise ValueError("model_id is None")
        else:
            self.model_id = model_id
        
        if kwargs is not None:
            self.kwargs = kwargs

    def get_ai_rsp(self,keywords:str|list|None = None):
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=os.environ.get("ARK_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        if keywords is None:
            if isinstance(self.keywords, str):
                keywords = [self.keywords]
            elif isinstance(self.keywords, list):
                keywords = self.keywords
            else:
                raise TypeError("keyword must be str or list")
        else:
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
            model=self.model_id,  # your model endpoint ID
            messages=[
                {"role": "system", "content": self.system_role_content},
                {"role": "user", "content": "\n".join(keywords)},
            ],
            stream=self.stream,
        )
        if self.stream:
            rsp = ""
            for chunk in completion:
                rsp += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="")
        else:
            rsp = completion.choices[0].message.content
        print(f"本轮数据已返回,耗时间:{time.time() - start_time}")
        return [rsp]

    async def async_get_ai_rsp(self,keywords:str|list|None = None):
        # 使用 nullcontext 兼容有无信号量的情况
        semaphore = self.kwargs.get('semaphore')
        ctx = semaphore if isinstance(semaphore, asyncio.Semaphore) else nullcontext()
        if keywords is None:
            keywords = self.keywords

        async with ctx:
            client = AsyncOpenAI(
                api_key = os.environ.get("ARK_API_KEY"),
                base_url = "https://ark.cn-beijing.volces.com/api/v3",
            )
            if isinstance(keywords,str):
                keywords = [keywords]
            elif isinstance(keywords,list):
                pass
            else:
                raise TypeError('keyword must be str or list')

            # Non-streaming:
            print("----- standard request -----")
            start_time = time.time()
            completion = await client.chat.completions.create(
                model = self.model_id,  # your model endpoint ID
                messages = [
                    {"role": "system", "content": self.system_role_content},
                    {"role": "user", "content": '\n'.join(keywords)},
                ],
                stream=False
            )
            rsp = completion.choices[0].message.content
            print(f'\n本轮数据已返回,耗时间:{time.time()-start_time}\n')
            return rsp
                

    def upload_file(self,file_path:str|Path):
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=os.environ.get("ARK_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        with open(file_path, "rb") as file:
            response = client.files.create(
                file=file,
                purpose="assistants"  # 用于助手API的文件
            )
        print(f"文件上传成功,文件ID:{response.id}")
        return response.id
    
    def assistant_agent(self,file_id:str):
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=os.environ.get("ARK_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        # 创建带有文件的助手
        assistant = client.beta.assistants.create(
            name="文档解析助手",
            instructions="你是一个擅长解析和总结文档内容的助手",
            tools=[{"type": "retrieval"}],  # 启用检索功能
            model=self.model_id,  # 或其他支持的模型
            file_ids=[file_id]  # 使用上传的文件
        )
        # 创建线程并提问
        thread = client.beta.threads.create()

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=self.system_role_content
        )
        # 运行助手
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        # 检查运行状态并获取结果
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            time.sleep(2)  # 等待2秒再检查

        # 获取助手的回复
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for message in messages.data:
            if message.role == "assistant":
                print(message.content[0].text.value)
        print(f" assistant_agent:{assistant}")