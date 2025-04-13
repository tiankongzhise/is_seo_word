from ..datebase.curd import CURD
from ..datebase.models import KeywordWithRegionTable
from ..models import FileInfo,KeywordWithRegion
from ..utils import (
    format_rsp,
    formated_rsp_to_dict_list,
    deduplicate_by_unique_constraints
)



def save_rsp_result(rsp:str,client:CURD,file_info:FileInfo,ai_model:str):
    try:
        local_rsp_file_path = file_info.local_rsp_file_path
        fail_rsp_file_path = file_info.local_format_fail_file_path
        
        with open(local_rsp_file_path,'a',encoding='utf-8') as f:
            f.write(rsp)
        json_str = format_rsp(rsp,ai_model=ai_model)
        formated_item = formated_rsp_to_dict_list(json_str)
        if formated_item is None:
            with open(fail_rsp_file_path,'a',encoding='utf-8') as f:
                f.write(rsp)
            return None
        mapping_dict = {
            '关键词':'keyword',
            '区域':'region',
            '层级':'region_level',
            '归属地级':'city_name',
            '归属省级':'province_name',
        }

        filtered_result = deduplicate_by_unique_constraints(orm_model=KeywordWithRegionTable,result=formated_item,mapping_dict=mapping_dict)
        temp_list = []
        try:
            for item in filtered_result:
                temp_list.append(KeywordWithRegion(keyword=item['关键词'],
                                                        region=item['区域'],
                                                        region_level=item['层级'],
                                                        city_name=item['归属地级'],
                                                        province_name=item['归属省级'],
                                                        ai_model=ai_model)
                                                        )
            client.bulck_insert_keyword_with_region(temp_list)
            return True
        except Exception as e:
            print(f'数据库写入失败,原因为{e},rsp为{rsp}')
            with open(fail_rsp_file_path,'a',encoding='utf-8') as f:
                f.write(rsp)
            return False
    except Exception as e:
        print(e)
        print(f'rsp为{rsp}')
        print(f'file_info为{file_info}')
        print(f'ai_model为{ai_model}')
        return False