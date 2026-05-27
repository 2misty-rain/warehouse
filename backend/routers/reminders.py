from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from auth import get_current_user
from schemas import ReminderCreate, ReminderResponse
from crud import get_reminders, create_reminder, update_reminder_status, delete_reminder

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("", response_model=List[ReminderResponse])
def read_reminders(is_processed: Optional[bool] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_reminders(db, is_processed=is_processed)


@router.post("", response_model=ReminderResponse)
def create_reminder_item(reminder: ReminderCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return create_reminder(db=db, reminder=reminder)


@router.put("/{reminder_id}")
def update_reminder_item(reminder_id: int, is_processed: bool, db: Session = Depends(get_db), user=Depends(get_current_user)):
    reminder = update_reminder_status(db, reminder_id=reminder_id, is_processed=is_processed)
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {"message": "提醒状态更新成功"}


@router.delete("/{reminder_id}")
def delete_reminder_item(reminder_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    success = delete_reminder(db, reminder_id=reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {"message": "提醒删除成功"}
