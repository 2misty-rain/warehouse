from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import DashboardStats
from auth import get_current_user
from crud import get_dashboard_stats, get_sales_trend

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_statistics(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_dashboard_stats(db)


@router.get("/sales")
def get_sales_trend_data(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_sales_trend(db)
