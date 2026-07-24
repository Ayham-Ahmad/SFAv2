import json
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import User, Interaction, Company, TentDatabase
from ..schemas.interactions import DashboardOut
from ..schemas.companies import MODEL_PRICING


class Dashboard:

    @staticmethod
    def get_stats(db: Session) -> DashboardOut:

        total_active_users = (
            db.query(func.count(User.user_id))
            .filter(User.is_active.is_(True))
            .scalar()
        )

        total_companies = (
            db.query(func.count(Company.company_id))
            .scalar()
        )

        interactions = db.query(Interaction).all()
        total_llm_cost = 0.0
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
                try:
                    from api.constants import AIModel
                    ai_model = AIModel(model_name)
                    rates = MODEL_PRICING.get(ai_model)
                    if rates:
                        total_llm_cost += (
                            (tokens.get("p_tokens", 0) / 1_000_000) * rates.input_cost_per_1m
                            + (tokens.get("c_tokens", 0) / 1_000_000) * rates.output_cost_per_1m
                        )
                except (ValueError, KeyError):
                    pass

        total_active_databases = (
            db.query(func.count(TentDatabase.db_id))
            .filter(TentDatabase.is_active.is_(True))
            .scalar()
        )

        total_interactions = (
            db.query(func.count(Interaction.interaction_id))
            .scalar()
        )

        return DashboardOut(
            active_users=total_active_users or 0,
            companies=total_companies or 0,
            llm_cost=round(total_llm_cost, 2),
            active_databases=total_active_databases or 0,
            total_interactions=total_interactions or 0,
        )
