"""Task service - business logic for task management."""
import datetime
import hashlib
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Task, TaskRun, Script, RunLog
from app.schemas import TaskCreate, TaskUpdate
from app.utils.script_generator import generate_crawl_script, generate_parse_script, generate_full_script, save_script


def generate_spider_name(url: str, task_id: int) -> str:
    """Generate unique spider name using URL MD5 + task_id."""
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
    return f"spider_{task_id}_{md5}"


class TaskService:

    @staticmethod
    def list_tasks(db: Session, group: str = None, status: str = None, task_type: str = None,
                         page: int = 1, page_size: int = 20) -> dict:
        query = select(Task)
        count_query = select(func.count(Task.id))

        if group:
            query = query.where(Task.group_name == group)
            count_query = count_query.where(Task.group_name == group)
        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)
        if task_type:
            query = query.where(Task.task_type == task_type)
            count_query = count_query.where(Task.task_type == task_type)

        total = (db.execute(count_query)).scalar() or 0
        query = query.order_by(Task.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = db.execute(query)
        tasks = result.scalars().all()

        # 从数据表实际查询采集量和解析量
        import pymysql as _pymysql
        from app.config import settings as _settings
        items = []
        for t in tasks:
            task_dict = {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            cfg = t.config_json or {}
            spider_name = cfg.get("spider_name", "")
            db_table = cfg.get("db_table", "") or "crawler_feachdata"  # 默认表名

            # 如果spider_name为空，根据task_id生成
            if not spider_name and task_dict.get("id"):
                from app.service.task_service import generate_spider_name
                url = cfg.get("url", "")
                spider_name = generate_spider_name(url, task_dict["id"])

            db_host = cfg.get("db_host")
            db_port = cfg.get("db_port")
            db_user = cfg.get("db_user")
            db_password = cfg.get("db_password")
            db_name = cfg.get("db_name")

            # 如果config中没有数据库信息，从datasource获取
            if not db_host and cfg.get("datasource_id"):
                try:
                    from app.models.datasource import DataSource
                    ds = db.query(DataSource).filter(DataSource.id == cfg["datasource_id"]).first()
                    if ds:
                        db_host = ds.host
                        db_port = ds.port
                        db_user = ds.username
                        db_password = ds.password
                        db_name = ds.database_name
                except:
                    pass

            # 最后fallback到默认配置
            db_host = db_host or _settings.DB_HOST
            db_port = db_port or _settings.DB_PORT
            db_user = db_user or _settings.DB_USER
            db_password = db_password or _settings.DB_PASSWORD
            db_name = db_name or _settings.DB_NAME

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
                    task_dict["total_crawled"] = count_crawled
                    task_dict["total_parsed"] = count_parsed
                    # 同步更新tasks表缓存
                    if t.total_crawled != count_crawled or t.total_parsed != count_parsed:
                        db.execute(
                            Task.__table__.update().where(Task.id == t.id).values(
                                total_crawled=count_crawled, total_parsed=count_parsed
                            )
                        )
                        db.commit()
                except Exception as e:
                    print(f"[WARN] 查询任务{t.id}采集量失败: {e}")
            items.append(task_dict)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def get_task(db: Session, task_id: int) -> Optional[Task]:
        result = db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    def create_task(db: Session, data: TaskCreate, user_id: int = None) -> Task:
        task = Task(
            name=data.name,
            description=data.description,
            task_type=getattr(data, 'task_type', 'professional'),
            group_name=data.group_name,
            engine=data.engine,
            config_json=data.config_json,
            datasource_id=getattr(data, 'datasource_id', None),
            created_by=user_id,
        )
        db.add(task)
        db.flush()

        # Generate spider_name and add to config
        config = data.config_json or {}
        url = config.get("url", "")
        spider_name = generate_spider_name(url, task.id)
        config["spider_name"] = spider_name
        config["engine"] = data.engine
        config["task_name"] = data.name  # 任务名称，用于tag字段
        task.config_json = config

        # Auto-generate scripts
        crawl_code = generate_crawl_script(task.id, config)
        crawl_path = save_script(task.id, "crawl", crawl_code)
        db.add(Script(task_id=task.id, script_type="crawl", code=crawl_code, file_path=crawl_path))

        parse_code = generate_parse_script(task.id, config)
        parse_path = save_script(task.id, "parse", parse_code)
        db.add(Script(task_id=task.id, script_type="parse", code=parse_code, file_path=parse_path))

        full_code = generate_full_script(task.id, config)
        full_path = save_script(task.id, "full", full_code)
        db.add(Script(task_id=task.id, script_type="full", code=full_code, file_path=full_path))

        return task

    @staticmethod
    def update_task(db: Session, task_id: int, data: TaskUpdate) -> Optional[Task]:
        task = TaskService.get_task(db, task_id)
        if not task:
            return None
        update_data = data.model_dump(exclude_unset=True)

        # Update config_json and regenerate spider_name if url changed
        config_changed = False
        if "config_json" in update_data:
            config = update_data["config_json"] or {}
            url = config.get("url", "")
            if url and "spider_name" not in config:
                config["spider_name"] = generate_spider_name(url, task_id)
                update_data["config_json"] = config
            # 确保task_name在config中
            if "task_name" not in config:
                config["task_name"] = task.name
                update_data["config_json"] = config
            config_changed = True

        for k, v in update_data.items():
            setattr(task, k, v)
        task.updated_at = datetime.datetime.utcnow()

        # 当配置变更时，重新生成所有脚本
        if config_changed:
            config = task.config_json or {}
            config["engine"] = task.engine
            for script_type, gen_func in [
                ("crawl", generate_crawl_script),
                ("parse", generate_parse_script),
                ("full", generate_full_script),
            ]:
                try:
                    code = gen_func(task_id, config)
                    filepath = save_script(task_id, script_type, code)
                    sr = db.execute(select(Script).where(Script.task_id == task_id, Script.script_type == script_type))
                    script = sr.scalar_one_or_none()
                    if script:
                        script.code = code
                        script.file_path = filepath
                        script.version += 1
                    else:
                        db.add(Script(task_id=task_id, script_type=script_type, code=code, file_path=filepath))
                except Exception as e:
                    print(f"Regenerate {script_type} failed: {e}")

        return task

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        task = TaskService.get_task(db, task_id)
        if not task:
            return False
        db.delete(task)
        return True

    @staticmethod
    def create_run(db: Session, task_id: int, trigger: str = "manual") -> TaskRun:
        run = TaskRun(task_id=task_id, trigger=trigger, status="pending", started_at=datetime.datetime.utcnow())
        db.add(run)
        db.flush()
        # Update task status
        task = TaskService.get_task(db, task_id)
        if task:
            task.status = "running"
        return run

    @staticmethod
    def finish_run(db: Session, run_id: int, status: str, error: str = None, summary: dict = None):
        result = db.execute(select(TaskRun).where(TaskRun.id == run_id))
        run = result.scalar_one_or_none()
        if run:
            run.status = status
            run.finished_at = datetime.datetime.utcnow()
            if run.started_at:
                run.duration_seconds = (run.finished_at - run.started_at).total_seconds()
            run.error_message = error
            run.result_summary = summary
            task = TaskService.get_task(db, run.task_id)
            if task:
                task.status = "idle"
                task.last_run_at = datetime.datetime.utcnow()

    @staticmethod
    def get_runs(db: Session, task_id: int) -> List[TaskRun]:
        result = db.execute(
            select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.started_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    def get_groups(db: Session) -> List[str]:
        result = db.execute(select(Task.group_name).distinct())
        return [r[0] for r in result.all()]
