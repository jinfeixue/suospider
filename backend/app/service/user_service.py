"""User service - authentication and user management."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import hash_password, verify_password, create_access_token


class UserService:

    @staticmethod
    async def authenticate(db: AsyncSession, username: str, password: str) -> Optional[dict]:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            return None
        token = create_access_token({"sub": user.username, "role": user.role})
        return {"access_token": token, "token_type": "bearer", "user": {
            "id": user.id, "username": user.username, "role": user.role
        }}

    @staticmethod
    async def create_user(db: AsyncSession, username: str, password: str, role: str = "operator") -> User:
        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def get_user(db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def init_default_admin(db: AsyncSession):
        """Create default admin user if no users exist."""
        result = await db.execute(select(User))
        if result.scalar_one_or_none() is None:
            await UserService.create_user(db, "admin", "admin123", "admin")

    @staticmethod
    def authenticate_sync(db: Session, username: str, password: str) -> Optional[dict]:
        """同步认证（用于Windows兼容）"""
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        token = create_access_token({"sub": user.username, "role": user.role})
        return {"access_token": token, "token_type": "bearer", "user": {
            "id": user.id, "username": user.username, "role": user.role
        }}

    @staticmethod
    def create_user_sync(db: Session, username: str, password: str, role: str = "operator") -> User:
        """同步创建用户（用于Windows兼容）"""
        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def get_user_sync(db: Session, username: str) -> Optional[User]:
        """同步获取用户（用于Windows兼容）"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def init_default_admin_sync(db: Session):
        """Create default admin user if no users exist (同步版本)."""
        if db.query(User).first() is None:
            UserService.create_user_sync(db, "admin", "admin123", "admin")
