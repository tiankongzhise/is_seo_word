from pydantic import BaseModel,Field
from decimal import Decimal
from pathlib import Path

from dataclasses import dataclass

@dataclass
class FileInfo:
    local_rsp_file_path:Path
    local_format_fail_file_path:Path


# 关键词生造评分
class KeywordScore(BaseModel):
    keyword:str = Field(...,description="关键词")
    score:Decimal = Field(...,description="关键词评分")


class KeywordScoreWithReason(BaseModel):
    keyword:str = Field(...,description="关键词")
    reason:str = Field(...,description="关键词评分原因")
    score:int = Field(...,description="关键词评分")
    ai_model:str = Field(...,description="关键词评分使用的模型")



class KeywordWithRegion(BaseModel):
    keyword:str = Field(...,description="关键词")
    region:str = Field(...,description="关键词所属区域")
    region_level:str = Field(...,description="关键词所属区域等级")
    city_name:str = Field(...,description="所属地级区域名称")
    province_name:str = Field(...,description="所属省级区域名称")
    ai_model:str = Field(...,description="关键词评分使用的模型")
