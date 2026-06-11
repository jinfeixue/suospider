"""Auth API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas import LoginRequest
from app.service.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = UserService.authenticate_sync(db, data.username, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"code": 0, "data": result}


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    return {"code": 0, "data": user}
