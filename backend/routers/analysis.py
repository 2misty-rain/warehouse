from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from schemas import AnalysisQuery, AnalysisResponse
from crud import (
    get_weekly_report, get_monthly_report, get_sales_analysis,
    get_inventory_count
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/weekly-report")
def weekly_report(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_weekly_report(db)


@router.get("/monthly-report")
def monthly_report(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_monthly_report(db)


@router.get("/sales-analysis")
def sales_analysis(time_range: str = "全部", group_by: str = None,
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_sales_analysis(db, time_range=time_range, group_by=group_by)


@router.post("/query", response_model=AnalysisResponse)
def analysis_query(request: AnalysisQuery, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """AI驱动的自由统计分析查询"""
    from ai.agent import run as agent_run
    result = agent_run(db, request.query, user_id="analysis")
    return {
        "success": result.get("success", False),
        "query": request.query,
        "answer": result.get("reply", ""),
        "data": result.get("data")
    }
