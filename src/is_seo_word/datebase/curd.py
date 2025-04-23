from tkzs_bd_db_tool import init_db,get_session
from typing import List
from ..models import KeywordScore,KeywordScoreWithReason,KeywordWithRegion,SchoolObject
from .models import KeywordSeoScore,KeywordBuyScore,KeywordSeoScoreWithReason,KeywordWithRegionTable,SchoolObjectTable



class CURD(object):
    def __init__(self):
        init_db()
    
    def bluck_insert_keyword_seo_score(self, data:List[KeywordScore]):
        with get_session() as session:
            insert_data = [item.model_dump() for item in data]
            session.bulk_insert_mappings(KeywordSeoScore, insert_data)

    def bulck_insert_keyword_buy_score(self, data:List[KeywordScore]):
        with get_session() as session:
            insert_data = [item.model_dump() for item in data]
            session.bulk_insert_mappings(KeywordBuyScore, insert_data)
    def bulck_insert_keyword_seo_score_with_reason(self, data:List[KeywordScoreWithReason]):
        with get_session() as session:
            insert_data = [item.model_dump() for item in data]
            session.bulk_insert_mappings(KeywordSeoScoreWithReason, insert_data)
    
    def query_keyword_in_keyword_seo_score_with_reason(self)->List[str]:
        with get_session() as session:
            rsp = session.query(KeywordSeoScoreWithReason.keyword).all()
            return [str(item[0]).lower() for item in rsp]
    def query_keyword_in_keyword_with_region(self)->List[str]:
        with get_session() as session:
            rsp = session.query(KeywordWithRegionTable.keyword).all()
            return [str(item[0]).lower() for item in rsp]
    
    def bulck_insert_keyword_with_region(self, data:List[KeywordWithRegion]):
        with get_session() as session:
            insert_data = [item.model_dump() for item in data]
            session.bulk_insert_mappings(KeywordWithRegionTable, insert_data)
    
    def query_keyword_in_school_object(self)->List[str]:
        with get_session() as session:
            rsp = session.query(SchoolObjectTable.school_name).all()
            return [str(item[0]).lower() for item in rsp]
    def bluck_insert_school_object(self, data:List[SchoolObject]):
        with get_session() as session:
            insert_data = [item.model_dump() for item in data]
            session.bulk_insert_mappings(SchoolObjectTable, insert_data)