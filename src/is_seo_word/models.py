from pydantic import BaseModel,Field
from decimal import Decimal
from pathlib import Path

from dataclasses import dataclass
# 关键词生造评分
class KeywordScore(BaseModel):
    keyword:str = Field(...,description="关键词")
    score:Decimal = Field(...,description="关键词评分")


class KeywordScoreWithReason(BaseModel):
    keyword:str = Field(...,description="关键词")
    reason:str = Field(...,description="关键词评分原因")
    score:int = Field(...,description="关键词评分")

@dataclass
class FileInfo:
    local_rsp_file_path:Path
    local_format_fail_file_path:Path
