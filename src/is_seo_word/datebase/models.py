from tkzs_bd_db_tool.models import Base
from sqlalchemy import Column, Integer, String, DateTime, DECIMAL,func,UniqueConstraint

class KeywordSeoScore(Base):
    __tablename__ = 'keyword_seo_score'
    __table_args__ = (
        UniqueConstraint('keyword', name='unique_keyword'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_0900_ai_ci',
            'schema': 'ads_dim_db'
        }

    )

    key_id = Column(Integer, primary_key=True, autoincrement=True,comment='主键')

    keyword = Column(String(255), nullable=False, comment='关键词')
    score = Column(DECIMAL(4,2), nullable=False, comment='关键词评分')

    create_at = Column(DateTime, nullable=True,default=func.now(), comment='创建时间')
    update_at = Column(DateTime, nullable=True,onupdate=func.now(), comment='更新时间')

class KeywordBuyScore(Base):
    __tablename__ = 'keyword_buy_score'
    __table_args__ = (
        UniqueConstraint('keyword', name='unique_keyword'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_0900_ai_ci',
            'schema': 'ads_dim_db'
        }
    )
    key_id = Column(Integer, primary_key=True, autoincrement=True,comment='主键')
    keyword = Column(String(255), nullable=False, comment='关键词')
    score = Column(DECIMAL(4,2), nullable=False, comment='关键词评分')
    create_at = Column(DateTime, nullable=True,default=func.now(), comment='创建时间')
    update_at = Column(DateTime, nullable=True,onupdate=func.now(), comment='更新时间')
    
