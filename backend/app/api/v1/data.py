"""Data export API routes."""
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db, get_sync_session
from app.core.security import get_current_user
from app.utils.export import export_json, export_excel
from app.config import settings

router = APIRouter(prefix="/data", tags=["Data"])


class DbConfig(BaseModel):
    host: str
    port: int
    database: str
    table: str
    user: str = "root"
    password: str = ""


# 标准表结构
STANDARD_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `spider_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '爬虫任务标识',
  `title` longtext COLLATE utf8mb4_unicode_ci,
  `title_eng` longtext COLLATE utf8mb4_unicode_ci,
  `url` longtext COLLATE utf8mb4_unicode_ci,
  `abstract` longtext COLLATE utf8mb4_unicode_ci,
  `abstract_eng` longtext COLLATE utf8mb4_unicode_ci,
  `author_addrs` longtext COLLATE utf8mb4_unicode_ci,
  `author` longtext COLLATE utf8mb4_unicode_ci,
  `fenleihao` longtext COLLATE utf8mb4_unicode_ci,
  `content` longtext COLLATE utf8mb4_unicode_ci,
  `html` longtext COLLATE utf8mb4_unicode_ci,
  `keyword` longtext COLLATE utf8mb4_unicode_ci,
  `keyword_eng` longtext COLLATE utf8mb4_unicode_ci,
  `jijin` longtext COLLATE utf8mb4_unicode_ci,
  `meetingname` longtext COLLATE utf8mb4_unicode_ci,
  `meetingplace` longtext COLLATE utf8mb4_unicode_ci,
  `organizer` longtext COLLATE utf8mb4_unicode_ci,
  `mentor` longtext COLLATE utf8mb4_unicode_ci,
  `degree` longtext COLLATE utf8mb4_unicode_ci,
  `downloadnum` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `kanming_eng` longtext COLLATE utf8mb4_unicode_ci,
  `languages` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `viewnum` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `similar` longtext COLLATE utf8mb4_unicode_ci,
  `zuozhedanwei` longtext COLLATE utf8mb4_unicode_ci,
  `zuozhe` longtext COLLATE utf8mb4_unicode_ci,
  `kanming` longtext COLLATE utf8mb4_unicode_ci,
  `nianjuanqi` longtext COLLATE utf8mb4_unicode_ci,
  `chubanriqi` longtext COLLATE utf8mb4_unicode_ci,
  `parseflag` int(11) DEFAULT NULL,
  `attachmentcontent` longtext COLLATE utf8mb4_unicode_ci,
  `attachmenturl` longtext COLLATE utf8mb4_unicode_ci,
  `field1` longtext COLLATE utf8mb4_unicode_ci,
  `field2` longtext COLLATE utf8mb4_unicode_ci,
  `field3` longtext COLLATE utf8mb4_unicode_ci,
  `field4` longtext COLLATE utf8mb4_unicode_ci,
  `field5` longtext COLLATE utf8mb4_unicode_ci,
  `field6` longtext COLLATE utf8mb4_unicode_ci,
  `field7` longtext COLLATE utf8mb4_unicode_ci,
  `field8` longtext COLLATE utf8mb4_unicode_ci,
  `field9` longtext COLLATE utf8mb4_unicode_ci,
  `attachmentpath` longtext COLLATE utf8mb4_unicode_ci,
  `attachmentparseflag` int(11) DEFAULT NULL,
  `releasetime` datetime DEFAULT NULL,
  `tag` longtext COLLATE utf8mb4_unicode_ci,
  `solrid` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `diskimages` longtext COLLATE utf8mb4_unicode_ci,
  `wwwimages` longtext COLLATE utf8mb4_unicode_ci,
  `thumbdiskimages` longtext COLLATE utf8mb4_unicode_ci,
  `thumbwwwimages` longtext COLLATE utf8mb4_unicode_ci,
  `playerurl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `videourl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seedurl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `crawlerserverurl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `indexflag` int(11) DEFAULT NULL,
  `citations` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `knowledgeid` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jsondata` longtext COLLATE utf8mb4_unicode_ci,
  `creationtime` datetime DEFAULT NULL,
  `filesize` mediumtext COLLATE utf8mb4_unicode_ci,
  `lastmodifiedtime` datetime DEFAULT NULL,
  `pagecount` int(11) DEFAULT NULL,
  `upload_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_spider_name` (`spider_name`),
  UNIQUE KEY `idx_solrid` (`solrid`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=COMPACT;
"""


@router.post("/test-db")
async def test_database(data: DbConfig, user=Depends(get_current_user)):
    """测试数据库连接并获取表字段"""
    import pymysql
    try:
        conn = pymysql.connect(
            host=data.host,
            port=data.port,
            user=data.user,
            password=data.password or settings.DB_PASSWORD,
            database=data.database,
            charset='utf8mb4',
            connect_timeout=5
        )
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute(f"SHOW TABLES LIKE '{data.table}'")
        table_exists = cursor.fetchone() is not None
        
        columns = []
        if table_exists:
            # 获取表字段
            cursor.execute(f"DESCRIBE `{data.table}`")
            columns = [row[0] for row in cursor.fetchall() if row[0] != 'id']
        
        cursor.close()
        conn.close()
        
        return {
            "code": 0,
            "data": {
                "connected": True,
                "table_exists": table_exists,
                "columns": columns
            }
        }
    except Exception as e:
        return {"code": -1, "message": f"连接失败: {str(e)}"}


@router.post("/create-db")
async def create_database(data: DbConfig, user=Depends(get_current_user)):
    """创建数据库和表"""
    import pymysql
    try:
        # 先连接MySQL（不指定数据库）创建数据库
        conn = pymysql.connect(
            host=data.host,
            port=data.port,
            user=data.user,
            password=data.password or settings.DB_PASSWORD,
            charset='utf8mb4',
            connect_timeout=5
        )
        cursor = conn.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{data.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{data.database}`")
        
        # 创建表
        ddl = STANDARD_TABLE_DDL.format(table=data.table)
        cursor.execute(ddl)
        
        conn.commit()
        
        # 获取表字段
        cursor.execute(f"DESCRIBE `{data.table}`")
        columns = [row[0] for row in cursor.fetchall() if row[0] != 'id']
        
        cursor.close()
        conn.close()
        
        return {
            "code": 0,
            "message": f"数据库 '{data.database}' 和表 '{data.table}' 创建成功",
            "data": {
                "columns": columns
            }
        }
    except Exception as e:
        return {"code": -1, "message": f"创建失败: {str(e)}"}


@router.get("/stats/overview")
def data_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Get data statistics overview."""
    from sqlalchemy import select, func
    from app.models import Task, TaskRun

    total_tasks = (db.execute(select(func.count(Task.id)))).scalar() or 0
    running_tasks = (db.execute(
        select(func.count(Task.id)).where(Task.status == "running")
    )).scalar() or 0

    # 从实际数据表查询采集量和解析量
    import pymysql as _pymysql
    from app.config import settings as _settings
    
    result = db.execute(select(Task))
    tasks = result.scalars().all()
    
    total_crawled = 0
    total_parsed = 0
    for t in tasks:
        cfg = t.config_json or {}
        spider_name = cfg.get("spider_name", "")
        db_table = cfg.get("db_table", "")
        db_host = cfg.get("db_host", _settings.DB_HOST)
        db_port = cfg.get("db_port", _settings.DB_PORT)
        db_user = cfg.get("db_user", _settings.DB_USER)
        db_password = cfg.get("db_password", _settings.DB_PASSWORD)
        db_name = cfg.get("db_name", _settings.DB_NAME)
        
        if spider_name and db_table:
            try:
                conn = _pymysql.connect(
                    host=db_host, port=db_port, user=db_user,
                    password=db_password, database=db_name,
                    charset='utf8mb4', connect_timeout=10
                )
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT COUNT(*) FROM `{db_table}` WHERE spider_name = %s",
                    (spider_name,)
                )
                count_crawled = cursor.fetchone()[0]
                cursor.execute(
                    f"SELECT COUNT(*) FROM `{db_table}` WHERE spider_name = %s AND parseflag = 1",
                    (spider_name,)
                )
                count_parsed = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                total_crawled += count_crawled
                total_parsed += count_parsed
                # 同步更新tasks表缓存
                if t.total_crawled != count_crawled or t.total_parsed != count_parsed:
                    db.execute(
                        Task.__table__.update().where(Task.id == t.id).values(
                            total_crawled=count_crawled, total_parsed=count_parsed
                        )
                    )
                    db.commit()
            except Exception:
                # 查询失败时使用tasks表缓存值
                total_crawled += t.total_crawled or 0
                total_parsed += t.total_parsed or 0
        else:
            total_crawled += t.total_crawled or 0
            total_parsed += t.total_parsed or 0

    # Also return recent runs for dashboard
    result = db.execute(
        select(TaskRun).order_by(TaskRun.started_at.desc()).limit(10)
    )
    recent_runs = []
    for r in result.scalars().all():
        recent_runs.append({
            "id": r.id,
            "task_id": r.task_id,
            "trigger": r.trigger,
            "status": r.status,
            "started_at": str(r.started_at) if r.started_at else None,
            "finished_at": str(r.finished_at) if r.finished_at else None,
            "duration_seconds": r.duration_seconds,
        })

    return {"code": 0, "data": {
        "total_tasks": total_tasks,
        "running_tasks": running_tasks,
        "total_crawled": total_crawled,
        "total_parsed": total_parsed,
        "recent_runs": recent_runs,
    }}


@router.get("/runs/recent")
def get_recent_runs(
    limit: int = Query(50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get recent task runs across all tasks."""
    from sqlalchemy import select
    from app.models import TaskRun

    result = db.execute(
        select(TaskRun).order_by(TaskRun.started_at.desc()).limit(limit)
    )
    items = []
    for r in result.scalars().all():
        items.append({
            "id": r.id,
            "task_id": r.task_id,
            "trigger": r.trigger,
            "status": r.status,
            "started_at": str(r.started_at) if r.started_at else None,
            "finished_at": str(r.finished_at) if r.finished_at else None,
            "duration_seconds": r.duration_seconds,
        })
    return {"code": 0, "data": items}


@router.post("/export")
async def export_custom(data: dict, format: str = Query("json"), user=Depends(get_current_user)):
    """Export arbitrary data."""
    items = data.get("items", [])
    if format == "excel":
        filepath = export_excel(items)
    else:
        filepath = export_json(items)
    return FileResponse(
        path=filepath,
        filename=os.path.basename(filepath),
        media_type="application/octet-stream",
    )


@router.get("/task/{task_id}")
async def get_task_data(task_id: int, user=Depends(get_current_user)):
    """Get all data for a specific task from crawler database (filtered by spider_name)."""
    from app.models import Task
    from sqlalchemy import select
    
    # Get task config to find database info
    with get_sync_session() as db:
        result = db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    config = task.config_json or {}
    db_host = config.get("db_host", settings.DB_HOST)
    db_port = config.get("db_port", settings.DB_PORT)
    db_name = config.get("db_name", "")
    db_table = config.get("db_table", "crawler_feachdata")
    db_user = config.get("db_user", "root")
    db_password = config.get("db_password", settings.DB_PASSWORD)
    spider_name = config.get("spider_name", "")
    
    if not db_name:
        return {"code": 0, "data": []}
    
    import pymysql
    try:
        conn = pymysql.connect(
            host=db_host, port=db_port, user=db_user,
            password=db_password, database=db_name,
            charset='utf8mb4', connect_timeout=10
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        if spider_name:
            cursor.execute(f"SELECT * FROM `{db_table}` WHERE spider_name = %s ORDER BY id DESC LIMIT 1000", (spider_name,))
        else:
            cursor.execute(f"SELECT * FROM `{db_table}` ORDER BY id DESC LIMIT 1000")
        
        rows = cursor.fetchall()
        
        # Convert datetime objects to string
        for row in rows:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
        
        cursor.close()
        conn.close()
        
        return {"code": 0, "data": rows}
    except Exception as e:
        return {"code": -1, "message": str(e), "data": []}


@router.get("/task/{task_id}/export")
async def export_task_data(task_id: int, format: str = Query("excel"), user=Depends(get_current_user)):
    """Export data for a specific task."""
    from app.models import Task
    from sqlalchemy import select
    
    # Get task config
    with get_sync_session() as db:
        result = db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    config = task.config_json or {}
    db_host = config.get("db_host", settings.DB_HOST)
    db_port = config.get("db_port", settings.DB_PORT)
    db_name = config.get("db_name", "")
    db_table = config.get("db_table", "crawler_feachdata")
    db_user = config.get("db_user", "root")
    db_password = config.get("db_password", settings.DB_PASSWORD)
    
    if not db_name:
        raise HTTPException(status_code=400, detail="Task has no database configured")
    
    import pymysql
    try:
        conn = pymysql.connect(
            host=db_host, port=db_port, user=db_user,
            password=db_password, database=db_name,
            charset='utf8mb4', connect_timeout=10
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(f"SELECT * FROM `{db_table}` ORDER BY id DESC")
        rows = cursor.fetchall()
        
        # Convert datetime objects to string
        for row in rows:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    row[key] = str(value)
                elif value is None:
                    row[key] = ""
        
        cursor.close()
        conn.close()
        
        # Export
        if format == "excel":
            filepath = export_excel(rows, f"{task.name}_data.xlsx")
        else:
            filepath = export_json(rows, f"{task.name}_data.json")
        
        return FileResponse(
            path=filepath,
            filename=os.path.basename(filepath),
            media_type="application/octet-stream",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}")
async def get_data(run_id: int, user=Depends(get_current_user)):
    """Get collected data for a run."""
    # Read from result files
    result_dir = os.path.join(settings.RESULTS_DIR, str(run_id))
    if not os.path.exists(result_dir):
        return {"code": 0, "data": {"items": [], "total": 0}}

    json_file = os.path.join(result_dir, "results.json")
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"code": 0, "data": {"items": data, "total": len(data)}}

    return {"code": 0, "data": {"items": [], "total": 0}}


@router.get("/{run_id}/export")
async def export_data(run_id: int, format: str = Query("json"), user=Depends(get_current_user)):
    """Export collected data in specified format."""
    result_dir = os.path.join(settings.RESULTS_DIR, str(run_id))
    json_file = os.path.join(result_dir, "results.json")

    if not os.path.exists(json_file):
        raise HTTPException(status_code=404, detail="No data found for this run")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if format == "excel":
        filepath = export_excel(data, f"run_{run_id}_export.xlsx")
    else:
        filepath = export_json(data, f"run_{run_id}_export.json")

    return FileResponse(
        path=filepath,
        filename=os.path.basename(filepath),
        media_type="application/octet-stream",
    )
