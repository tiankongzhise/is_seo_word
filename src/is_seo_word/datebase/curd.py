from tkzs_bd_db_tool import init_db,get_session
from typing import List
from ..models import KeywordScore
from .models import KeywordSeoScore



class CURD(object):
    def __init__(self):
        init_db()
    
    def bluck_insert_keyword_seo_score(self, data:List[KeywordScore]):
        with get_session() as session:
            insert_data = [item.model_dump() for item in data]
            session.bulk_insert_mappings(KeywordSeoScore, insert_data)
