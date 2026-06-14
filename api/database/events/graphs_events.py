from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Union, Optional, List

from ...utils import to_dict
from ..models import GeneratedGraphs
from ...config import settings


class GraphsCRUD:

    @staticmethod
    def is_graph_limit_reached(db: Session, session_id: int) -> bool:
        count = (
            db.query(func.count(GeneratedGraphs.graph_id))
            .filter(GeneratedGraphs.session_id == session_id)
            .scalar()
        )
        return count >= settings.MAX_GRAPHS

    @staticmethod
    def create(db: Session, graph_data: Union[dict, any], user_id: int, session_id: int) -> Optional[GeneratedGraphs]:
        if GraphsCRUD.is_graph_limit_reached(db, session_id):
            return None 

        data = to_dict(graph_data) if not isinstance(graph_data, dict) else graph_data

        new_graph = GeneratedGraphs(
            graph_config=data,
            user_id=user_id,
            session_id=session_id,
        )
        db.add(new_graph)
        db.commit()
        db.refresh(new_graph)
        return new_graph

    @staticmethod
    def get_graphs_by_session(db: Session, session_id: int) -> List[GeneratedGraphs]:
        return (
            db.query(GeneratedGraphs)
            .filter(GeneratedGraphs.session_id == session_id)
            .order_by(GeneratedGraphs.created_at.asc())
            .all()
        )

    @staticmethod
    def get_graphs_by_user(db: Session, user_id: int) -> List[GeneratedGraphs]:
        return (
            db.query(GeneratedGraphs)
            .filter(GeneratedGraphs.user_id == user_id)
            .order_by(GeneratedGraphs.created_at.desc())
            .all()
        )

    @staticmethod
    def delete(db: Session, graph_id: int, user_id: int) -> bool:
        graph = (
            db.query(GeneratedGraphs)
            .filter(GeneratedGraphs.graph_id == graph_id, GeneratedGraphs.user_id == user_id)
            .first()
        )
        if not graph:
            return False
        db.delete(graph)
        db.commit()
        return True

    @staticmethod
    def delete_all_by_session(db: Session, session_id: int):
        db.query(GeneratedGraphs).filter(GeneratedGraphs.session_id == session_id).delete()
        db.commit()
