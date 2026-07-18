from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import User, Interaction, Company, TentDatabase
from ..schemas.interactions import DashboardOut

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

        total_llm_cost = (
            db.query(func.sum(Interaction.cost))
            .scalar()
        )

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
            llm_cost=total_llm_cost or 0.0,
            active_databases=total_active_databases or 0,
            total_interactions=total_interactions or 0,
        )