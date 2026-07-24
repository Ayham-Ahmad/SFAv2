from sqlalchemy.orm import Session
from sqlalchemy import func, case
from pydantic import BaseModel
import json
import sentry_sdk
from typing import Union, Optional, List, Dict, Any

from ..models import Interaction
from ...utils import to_dict
from ...constants import InteractionStatus, LlmUsageOut
from ..schemas.companies import MODEL_PRICING


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
        interactions = db.query(Interaction).all()

        model_tokens: Dict[str, Dict[str, int]] = {}
        model_calls: Dict[str, int] = {}
        model_response_times: Dict[str, List[float]] = {}
        model_memory: Dict[str, List[float]] = {}
        model_feedback_pos: Dict[str, int] = {}
        model_feedback_total: Dict[str, int] = {}

        for i in interactions:
            if not i.model_used:
                continue

            mu = i.model_used
            if isinstance(mu, str):
                try:
                    mu = json.loads(mu)
                except (json.JSONDecodeError, TypeError):
                    continue

            for model_name, tokens in mu.items():
                if model_name not in model_tokens:
                    model_tokens[model_name] = {"p_tokens": 0, "c_tokens": 0, "total_tokens": 0}
                    model_calls[model_name] = 0
                    model_response_times[model_name] = []
                    model_memory[model_name] = []
                    model_feedback_pos[model_name] = 0
                    model_feedback_total[model_name] = 0

                model_tokens[model_name]["p_tokens"] += tokens.get("p_tokens", 0)
                model_tokens[model_name]["c_tokens"] += tokens.get("c_tokens", 0)
                model_tokens[model_name]["total_tokens"] += tokens.get("total_tokens", 0)

            model_name = list(mu.keys())[0] if mu else None
            if model_name:
                model_calls[model_name] = model_calls.get(model_name, 0) + (i.api_call_count or 0)
                if i.response_time is not None:
                    model_response_times[model_name].append(i.response_time)
                if i.memory_usage is not None:
                    model_memory[model_name].append(i.memory_usage)
                if i.user_feedback is not None:
                    model_feedback_total[model_name] = model_feedback_total.get(model_name, 0) + 1
                    if i.user_feedback:
                        model_feedback_pos[model_name] = model_feedback_pos.get(model_name, 0) + 1

        usage_stats = {}
        for model_name, tokens in model_tokens.items():
            total_cost = 0.0
            try:
                from api.constants import AIModel
                ai_model = AIModel(model_name)
                rates = MODEL_PRICING.get(ai_model)
                if rates:
                    total_cost = round(
                        (tokens["p_tokens"] / 1_000_000) * rates.input_cost_per_1m
                        + (tokens["c_tokens"] / 1_000_000) * rates.output_cost_per_1m,
                        2,
                    )
            except (ValueError, KeyError):
                pass

            rt = model_response_times.get(model_name, [])
            mem = model_memory.get(model_name, [])
            pos = model_feedback_pos.get(model_name, 0)
            total_fb = model_feedback_total.get(model_name, 0)

            usage_stats[model_name] = {
                LlmUsageOut.COST.value: total_cost,
                LlmUsageOut.TOKENS.value: tokens["total_tokens"],
                LlmUsageOut.CALLS.value: model_calls.get(model_name, 0),
                LlmUsageOut.FEEDBACK.value: round((pos / total_fb) * 100, 2) if total_fb > 0 else 0.0,
                LlmUsageOut.ART.value: round(sum(rt) / len(rt), 3) if rt else 0.0,
                LlmUsageOut.AMU.value: round(sum(mem) / len(mem), 2) if mem else 0.0,
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
        model_used: Dict[str, Any],
        performance_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Interaction]:

        record = db.query(Interaction).filter(Interaction.interaction_id == interaction_id).first()
        if record:
            try:
                record.interaction_content = content
                record.agent_steps = steps
                record.model_used = model_used
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
