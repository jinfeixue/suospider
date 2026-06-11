"""LLMConfig API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.llm_config import LLMConfig
from app.schemas.llm_config import (
    LLMConfigCreate, LLMConfigUpdate, LLMConfigResponse, LLMTestResult
)
from app.service.llm_service import LLMService

router = APIRouter(prefix="/llm-config", tags=["大模型配置"])


def _config_to_dict(c):
    return {
        "id": c.id, "name": c.name, "provider": c.provider,
        "model": c.model, "api_url": c.api_url,
        "temperature": c.temperature, "max_tokens": c.max_tokens,
        "timeout": c.timeout, "is_default": c.is_default,
        "is_active": c.is_active,
        "created_at": str(c.created_at) if c.created_at else None,
        "updated_at": str(c.updated_at) if c.updated_at else None,
    }


@router.post("/")
def create_llm_config(data: LLMConfigCreate, db: Session = Depends(get_db)):
    """创建大模型配置"""
    config = LLMConfig(**data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return {"code": 0, "data": _config_to_dict(config)}


@router.get("/")
def list_llm_configs(db: Session = Depends(get_db)):
    """获取大模型配置列表"""
    configs = db.query(LLMConfig).all()
    items = [_config_to_dict(c) for c in configs]
    return {"code": 0, "data": items}


@router.get("/{config_id}")
def get_llm_config(config_id: int, db: Session = Depends(get_db)):
    """获取单个大模型配置"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"code": 0, "data": _config_to_dict(config)}


@router.put("/{config_id}")
def update_llm_config(config_id: int, data: LLMConfigUpdate, db: Session = Depends(get_db)):
    """更新大模型配置"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return {"code": 0, "data": _config_to_dict(config)}


@router.delete("/{config_id}")
def delete_llm_config(config_id: int, db: Session = Depends(get_db)):
    """删除大模型配置"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    db.delete(config)
    db.commit()
    return {"code": 0, "message": "删除成功"}


@router.post("/{config_id}/test")
def test_llm_config(config_id: int, db: Session = Depends(get_db)):
    """测试大模型配置连通性"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    import asyncio
    service = LLMService(
        provider=config.provider,
        model=config.model,
        api_key=config.api_key,
        api_url=config.api_url,
        timeout=config.timeout
    )
    try:
        result = asyncio.run(service.test_connection())
    except Exception as e:
        result = {"success": False, "message": str(e)}
    return {"code": 0, "data": result}


@router.post("/{config_id}/set-default")
def set_default_llm_config(config_id: int, db: Session = Depends(get_db)):
    """设置默认大模型配置"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    db.query(LLMConfig).filter(LLMConfig.is_default == True).update({"is_default": False})
    config.is_default = True
    db.commit()
    return {"code": 0, "message": "已设为默认配置"}
