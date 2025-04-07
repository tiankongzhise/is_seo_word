from pydantic import BaseModel,Field
from decimal import Decimal
# 关键词生造评分
class KeywordScore(BaseModel):
    keyword:str = Field(...,description="关键词")
    score:Decimal = Field(...,description="关键词评分")