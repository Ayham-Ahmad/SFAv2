from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_active_user
from ..database.models import User
from ..database.events.graphs_events import GraphsCRUD
from ..database.events.sessions_events import SessionCRUD
from backend.utils.responses import create_response

router = APIRouter(prefix="/api/graphs", tags=["Graphs"])


@router.get("/session")
async def get_session_graphs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    if not session:
        return create_response(True, data={"graphs": []})

    graphs = GraphsCRUD.get_graphs_by_session(db, session.session_id)
    return create_response(True, data={"graphs": [g.graph_config for g in graphs]})


@router.delete("/{graph_id}")
async def delete_graph(
    graph_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    success = GraphsCRUD.delete(db, graph_id, current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Graph not found or access denied.")
    return create_response(True, "Graph deleted.")


@router.delete("/session/all")
async def delete_all_session_graphs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    if not session:
        return create_response(True, "No active session.")
    GraphsCRUD.delete_all_by_session(db, session.session_id)
    return create_response(True, "All session graphs deleted.")
