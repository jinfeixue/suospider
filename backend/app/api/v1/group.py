"""Group management API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Group

router = APIRouter(prefix="/groups", tags=["Groups"], dependencies=[Depends(get_current_user)])


class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: str


@router.get("")
def list_groups(db: Session = Depends(get_db)):
    """列出所有分组"""
    result = db.execute(select(Group).order_by(Group.sort_order, Group.id))
    groups = result.scalars().all()

    # 确保默认分组存在
    default_exists = any(g.name == "默认分组" for g in groups)
    if not default_exists:
        db.add(Group(name="默认分组", sort_order=0))
        db.commit()
        result = db.execute(select(Group).order_by(Group.sort_order, Group.id))
        groups = result.scalars().all()
    
    return {"code": 0, "data": [{"id": g.id, "name": g.name, "sort_order": g.sort_order} for g in groups]}


@router.get("/names")
def list_group_names(db: Session = Depends(get_db)):
    """列出所有分组名称（兼容旧接口）"""
    result = db.execute(select(Group).order_by(Group.sort_order, Group.id))
    groups = result.scalars().all()

    # 确保默认分组存在
    default_exists = any(g.name == "默认分组" for g in groups)
    if not default_exists:
        db.add(Group(name="默认分组", sort_order=0))
        db.commit()
        result = db.execute(select(Group).order_by(Group.sort_order, Group.id))
        groups = result.scalars().all()
    
    return {"code": 0, "data": [g.name for g in groups]}


@router.post("")
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    """创建分组"""
    # 检查是否已存在
    result = db.execute(select(Group).where(Group.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分组已存在")

    # 获取最大排序号
    max_order = (db.execute(select(func.max(Group.sort_order)))).scalar() or 0

    group = Group(name=data.name, sort_order=max_order + 1)
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return {"code": 0, "message": "分组创建成功", "data": {"id": group.id, "name": group.name}}


@router.put("/{group_id}")
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db)):
    """更新分组"""
    result = db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    if group.name == "默认分组":
        raise HTTPException(status_code=400, detail="不能修改默认分组")

    # 检查新名称是否已存在
    if data.name != group.name:
        existing = db.execute(select(Group).where(Group.name == data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="分组名称已存在")

    group.name = data.name
    db.commit()
    
    return {"code": 0, "message": "分组更新成功"}


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """删除分组"""
    result = db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    if group.name == "默认分组":
        raise HTTPException(status_code=400, detail="不能删除默认分组")

    # 将该分组下的任务移到默认分组
    from app.models import Task
    tasks_result = db.execute(select(Task).where(Task.group_name == group.name))
    tasks = tasks_result.scalars().all()
    for task in tasks:
        task.group_name = "默认分组"

    db.delete(group)
    db.commit()
    
    return {"code": 0, "message": "分组删除成功"}


@router.post("/reorder")
def reorder_groups(group_ids: list[int], db: Session = Depends(get_db)):
    """重新排序分组"""
    for i, group_id in enumerate(group_ids):
        result = db.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if group:
            group.sort_order = i

    db.commit()
    return {"code": 0, "message": "排序成功"}
