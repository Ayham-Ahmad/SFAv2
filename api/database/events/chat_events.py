from sqlalchemy.orm import Session
from sqlalchemy import func, case
from pydantic import BaseModel
import sentry_sdk
from typing import Union, Optional, List, Dict, Any

from ..models import Interaction
from ...utils import to_dict
from ...constants import InteractionStatus, LlmUsageOut

class InteractionCRUD:

    @staticmethod
    def create(db: Session, interaction_data: Union[dict, BaseModel]) -> Interaction:
        data = to_dict(interaction_data)
        new_interaction = Interaction(**data)
        try:
            db.add(new_interaction)
            db.commit()
            db.refresh(new_interaction)
            return new_interaction
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print(f"Error while creating interaction: {str(e)}")
            db.rollback()
            return None

    @staticmethod
    def get_session_history_by_count(db: Session, session_id: int, count: int) -> List[Interaction]:
        return db.query(Interaction)\
            .filter(Interaction.session_id == session_id)\
            .order_by(Interaction.created_at.desc())\
            .limit(count)\
            .all()

    @staticmethod
    def get_entire_session_history(db: Session, session_id: int) -> List[Interaction]:
        return db.query(Interaction)\
            .filter(Interaction.session_id == session_id)\
            .order_by(Interaction.created_at.asc())\
            .all()
    
    @staticmethod
    def get_llm_usage(db: Session):
        results = db.query(
            Interaction.model_used,
            func.sum(Interaction.cost).label("total_cost"),
            func.sum(Interaction.token_count).label("total_tokens"),
            func.sum(Interaction.api_call_count).label("total_calls"),
            func.avg(Interaction.response_time).label("avg_response_time"),
            func.avg(Interaction.memory_usage).label("avg_memory_usage"),
            func.count(case((Interaction.user_feedback == 1, 1))).label("PFB"),
            func.count(Interaction.user_feedback).label("TFB")
        ).group_by(Interaction.model_used).all()

        usage_stats = {}
        for row in results:
            feedback_score = round((row.PFB / row.TFB) * 100, 2) if row.TFB and row.TFB > 0 else 0.0
            
            usage_stats[row.model_used] = {
                LlmUsageOut.COST.value: round(row.total_cost or 0.0, 4),
                LlmUsageOut.TOKENS.value: row.total_tokens or 0,
                LlmUsageOut.CALLS.value: row.total_calls or 0,
                LlmUsageOut.FEEDBACK.value: feedback_score,
                LlmUsageOut.ART.value: round(row.avg_response_time or 0.0, 3),
                LlmUsageOut.AMU.value: round(row.avg_memory_usage or 0.0, 2)
            }

        return usage_stats
    
    @staticmethod
    def set_feedback(db: Session, interaction_id: int, feedback: bool) -> Optional[Interaction]:
        record = db.query(Interaction).filter(Interaction.interaction_id == interaction_id).first()
        if record:
            record.user_feedback = feedback
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    def complete_interaction(
        db: Session, 
        interaction_id: int, 
        content: Dict[str, Any], 
        steps: Dict[str, Any],
        model_used: str,
        cost: float, 
        performance_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Interaction]:
        
        record = db.query(Interaction).filter(Interaction.interaction_id == interaction_id).first()
        if record:
            try:
                record.interaction_content = content
                record.agent_steps = steps
                record.model_used = model_used
                record.cost = cost
                record.status = InteractionStatus.COMPLETED
                
                if performance_data:
                    for key, value in performance_data.items():
                        if hasattr(record, key):
                            setattr(record, key, value)
                
                db.commit()
                db.refresh(record)
            except Exception as e:
                db.rollback()
                sentry_sdk.capture_exception(e)
                return None
        return record

    @staticmethod
    def mark_failed(db: Session, interaction_id: int) -> Optional[Interaction]:
        record = db.query(Interaction).filter(Interaction.interaction_id == interaction_id).first()
        if record:
            record.status = InteractionStatus.FAILED
            db.commit()
            db.refresh(record)
        return record
    
    @staticmethod
    def get_llm_cost(db: Session) -> float:
        total_cost = db.query(func.sum(Interaction.cost)).scalar()
        total_interactions = db.query(func.sum(Interaction.interaction_id)).scalar()

        return {"cost": total_cost, 'interactions': total_interactions}