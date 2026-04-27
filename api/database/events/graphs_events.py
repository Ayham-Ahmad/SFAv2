from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Union, Optional, List
from pydantic import BaseModel

from ...utils import to_dict
from ..models import GeneratedGraphs
from ...config import settings

class GraphsCRUD:
    
    @staticmethod
    def is_graph_limit(db: Session, user_id: int) -> bool:
        count = db.query(func.count(GeneratedGraphs.graph_id))\
            .filter(GeneratedGraphs.user_id == user_id)\
            .scalar()
            
        return count >= settings.MAX_GRAPHS
    
    @staticmethod
    def create(db: Session, graph_data: Union[dict, BaseModel], user_id: int) -> GeneratedGraphs:
        
        if GraphsCRUD.is_graph_limit(db, user_id):
            return "User reached the limit of graphs to generate"
        
        
        data = to_dict(graph_data)
        
        new_graph = GeneratedGraphs(
            graph_config=data,
            user_id=user_id
        )
        
        db.add(new_graph)
        db.commit()
        return new_graph
    
    @staticmethod
    def get_graphs(db: Session, user_id: int):
        return db.query(GeneratedGraphs).filter(GeneratedGraphs.user_id == user_id)
    
    @staticmethod
    def update(db: Session):
        pass
    
    @staticmethod
    def delete(db: Session):
        pass