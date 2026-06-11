"""DataSource API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.datasource import DataSource
from app.schemas.datasource import DataSourceCreate, DataSourceUpdate
import pymysql
from datetime import datetime

router = APIRouter(prefix="/datasource", tags=["数据源管理"])


def _ds_to_dict(s):
    return {
        "id": s.id, "name": s.name, "host": s.host,
        "port": s.port, "username": s.username,
        "password": s.password,  # 返回密码用于任务配置
        "database_name": s.database_name, "charset": s.charset,
        "is_active": s.is_active,
        "created_at": str(s.created_at) if s.created_at else None,
        "updated_at": str(s.updated_at) if s.updated_at else None,
    }


@router.post("/")
def create_datasource(data: DataSourceCreate, db: Session = Depends(get_db)):
    """创建数据源"""
    db_name = data.database_name or f"crawler_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    datasource = DataSource(
        name=data.name, host=data.host, port=data.port,
        username=data.username, password=data.password,
        database_name=db_name, charset=data.charset
    )
    db.add(datasource)
    db.commit()
    db.refresh(datasource)

    # 自动初始化数据库和表
    init_msg = ""
    try:
        conn = pymysql.connect(
            host=datasource.host, port=datasource.port,
            user=datasource.username, password=datasource.password,
            charset=datasource.charset, connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{datasource.database_name}` "
            f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{datasource.database_name}`")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        cursor.close()
        conn.close()
        init_msg = "，数据库和表已自动创建"
    except Exception as e:
        init_msg = f"，数据库自动创建失败: {str(e)}"

    result = _ds_to_dict(datasource)
    result["init_message"] = init_msg
    return {"code": 0, "data": result}


@router.get("/")
def list_datasources(db: Session = Depends(get_db)):
    """获取数据源列表"""
    sources = db.query(DataSource).all()
    items = [_ds_to_dict(s) for s in sources]
    return {"code": 0, "data": items}


@router.get("/{datasource_id}")
def get_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """获取单个数据源"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return {"code": 0, "data": _ds_to_dict(datasource)}


@router.put("/{datasource_id}")
def update_datasource(datasource_id: int, data: DataSourceUpdate, db: Session = Depends(get_db)):
    """更新数据源"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(datasource, key, value)

    db.commit()
    db.refresh(datasource)
    return {"code": 0, "data": _ds_to_dict(datasource)}


@router.delete("/{datasource_id}")
def delete_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """删除数据源"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")

    db.delete(datasource)
    db.commit()
    return {"code": 0, "message": "删除成功"}


@router.post("/{datasource_id}/test")
def test_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """测试数据源连通性"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")

    try:
        start_time = datetime.now()
        conn = pymysql.connect(
            host=datasource.host, port=datasource.port,
            user=datasource.username, password=datasource.password,
            charset=datasource.charset, connect_timeout=5
        )
        conn.close()
        response_time = (datetime.now() - start_time).total_seconds()
        return {"code": 0, "data": {"success": True, "message": "连接成功", "response_time": response_time}}
    except Exception as e:
        return {"code": 0, "data": {"success": False, "message": f"连接失败: {str(e)}"}}


@router.post("/{datasource_id}/init-db")
def init_database(datasource_id: int, db: Session = Depends(get_db)):
    """初始化数据库和表"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")

    try:
        conn = pymysql.connect(
            host=datasource.host, port=datasource.port,
            user=datasource.username, password=datasource.password,
            charset=datasource.charset, connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{datasource.database_name}` "
            f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{datasource.database_name}`")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        cursor.close()
        conn.close()
        return {"code": 0, "message": f"数据库 {datasource.database_name} 和表初始化成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


# 字段名到中文描述的映射
FIELD_LABELS = {
    "title": "标题",
    "title_eng": "英文标题",
    "abstract": "摘要",
    "abstract_eng": "英文摘要",
    "content": "正文内容",
    "html": "原始HTML",
    "author": "作者",
    "zuozhe": "作者",
    "author_addrs": "英文作者单位",
    "zuozhedanwei": "作者单位",
    "organizer": "组织者",
    "mentor": "导师",
    "fenleihao": "分类号",
    "keyword": "关键词",
    "keyword_eng": "英文关键词",
    "kanming": "刊名",
    "kanming_eng": "英文刊名",
    "nianjuanqi": "年卷期",
    "chubanriqi": "出版日期",
    "degree": "学位",
    "jijin": "基金",
    "citations": "引用次数",
    "meetingname": "会议名称",
    "meetingplace": "会议地点",
    "diskimages": "磁盘图片路径",
    "wwwimages": "图片路径",
    "thumbdiskimages": "缩略图磁盘路径",
    "thumbwwwimages": "缩略图路径",
    "playerurl": "播放器URL",
    "videourl": "视频URL",
    "attachmentcontent": "附件内容",
    "attachmenturl": "附件URL",
    "attachmentpath": "附件本地路径",
    "downloadnum": "下载次数",
    "viewnum": "浏览次数",
    "similar": "相似度",
    "pagecount": "页数",
    "filesize": "文件大小",
    "tag": "标签",
    "languages": "语言",
    "field1": "扩展字段1",
    "field2": "扩展字段2",
    "field3": "扩展字段3",
    "field4": "扩展字段4",
    "field5": "扩展字段5",
    "field6": "扩展字段6",
    "field7": "扩展字段7",
    "field8": "扩展字段8",
    "field9": "扩展字段9",
}

# 需要排除的字段（系统字段，不需要用户配置）
EXCLUDED_FIELDS = {"id", "url", "spider_name", "parseflag", "attachmentparseflag",
                   "indexflag", "solrid", "releasetime", "creationtime",
                   "lastmodifiedtime", "upload_time", "seedurl", "crawlerserverurl",
                   "knowledgeid", "jsondata"}


@router.get("/{datasource_id}/columns")
def get_datasource_columns(datasource_id: int, db: Session = Depends(get_db)):
    """获取数据源表的可用字段列表"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")

    try:
        conn = pymysql.connect(
            host=datasource.host, port=datasource.port,
            user=datasource.username, password=datasource.password,
            database=datasource.database_name,
            charset=datasource.charset, connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM crawler_feachdata")
        columns = cursor.fetchall()
        conn.close()

        # 构建字段列表，排除系统字段
        fields = []
        for col in columns:
            col_name = col[0]
            if col_name in EXCLUDED_FIELDS:
                continue
            label = FIELD_LABELS.get(col_name, col_name)
            fields.append({
                "name": col_name,
                "label": f"{col_name} ({label})",
                "type": col[1],
            })

        return {"code": 0, "data": fields}
    except Exception as e:
        return {"code": 0, "data": [], "message": f"获取字段失败: {str(e)}"}


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `crawler_feachdata` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` longtext COLLATE utf8mb4_unicode_ci COMMENT '标题',
  `title_eng` longtext COLLATE utf8mb4_unicode_ci COMMENT '英文标题',
  `url` longtext COLLATE utf8mb4_unicode_ci COMMENT '页面URL',
  `abstract` longtext COLLATE utf8mb4_unicode_ci COMMENT '摘要',
  `abstract_eng` longtext COLLATE utf8mb4_unicode_ci COMMENT '英文摘要',
  `content` longtext COLLATE utf8mb4_unicode_ci COMMENT '正文内容',
  `html` longtext COLLATE utf8mb4_unicode_ci COMMENT '原始HTML',
  `author` longtext COLLATE utf8mb4_unicode_ci COMMENT '作者',
  `zuozhe` longtext COLLATE utf8mb4_unicode_ci COMMENT '作者(中文)',
  `author_addrs` longtext COLLATE utf8mb4_unicode_ci COMMENT '英文作者单位',
  `zuozhedanwei` longtext COLLATE utf8mb4_unicode_ci COMMENT '作者单位',
  `organizer` longtext COLLATE utf8mb4_unicode_ci COMMENT '组织者',
  `mentor` longtext COLLATE utf8mb4_unicode_ci COMMENT '导师',
  `fenleihao` longtext COLLATE utf8mb4_unicode_ci COMMENT '分类号',
  `keyword` longtext COLLATE utf8mb4_unicode_ci COMMENT '关键词',
  `keyword_eng` longtext COLLATE utf8mb4_unicode_ci COMMENT '英文关键词',
  `kanming` longtext COLLATE utf8mb4_unicode_ci COMMENT '刊名',
  `kanming_eng` longtext COLLATE utf8mb4_unicode_ci COMMENT '英文刊名',
  `nianjuanqi` longtext COLLATE utf8mb4_unicode_ci COMMENT '年卷期',
  `chubanriqi` longtext COLLATE utf8mb4_unicode_ci COMMENT '出版日期(字符串)',
  `degree` longtext COLLATE utf8mb4_unicode_ci COMMENT '学位',
  `jijin` longtext COLLATE utf8mb4_unicode_ci COMMENT '基金',
  `citations` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '引用次数',
  `meetingname` longtext COLLATE utf8mb4_unicode_ci COMMENT '会议名称',
  `meetingplace` longtext COLLATE utf8mb4_unicode_ci COMMENT '会议地点',
  `diskimages` longtext COLLATE utf8mb4_unicode_ci COMMENT '磁盘图片路径',
  `wwwimages` longtext COLLATE utf8mb4_unicode_ci COMMENT '图片相对路径({|}分割)',
  `thumbdiskimages` longtext COLLATE utf8mb4_unicode_ci COMMENT '缩略图磁盘路径',
  `thumbwwwimages` longtext COLLATE utf8mb4_unicode_ci COMMENT '缩略图相对路径',
  `playerurl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '播放器URL',
  `videourl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '视频URL',
  `attachmentcontent` longtext COLLATE utf8mb4_unicode_ci COMMENT '附件内容',
  `attachmenturl` longtext COLLATE utf8mb4_unicode_ci COMMENT '附件URL',
  `attachmentpath` longtext COLLATE utf8mb4_unicode_ci COMMENT '附件本地路径',
  `downloadnum` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '下载次数',
  `viewnum` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '浏览次数',
  `similar` longtext COLLATE utf8mb4_unicode_ci COMMENT '相似度',
  `pagecount` int DEFAULT NULL COMMENT '页数',
  `filesize` mediumtext COLLATE utf8mb4_unicode_ci COMMENT '文件大小',
  `spider_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '任务标识',
  `parseflag` int DEFAULT NULL COMMENT '解析标志',
  `attachmentparseflag` int DEFAULT NULL COMMENT '附件解析标志',
  `indexflag` int DEFAULT NULL COMMENT '索引标志',
  `releasetime` datetime DEFAULT NULL COMMENT '发布时间',
  `creationtime` datetime DEFAULT NULL COMMENT '创建时间',
  `lastmodifiedtime` datetime DEFAULT NULL COMMENT '最后修改时间',
  `upload_time` datetime DEFAULT NULL COMMENT '上传时间',
  `tag` longtext COLLATE utf8mb4_unicode_ci COMMENT '标签',
  `solrid` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'URL的MD5值',
  `seedurl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '种子URL',
  `crawlerserverurl` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '爬虫服务器URL',
  `knowledgeid` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '知识ID',
  `jsondata` longtext COLLATE utf8mb4_unicode_ci COMMENT 'JSON扩展数据',
  `languages` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '语言',
  `field1` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段1',
  `field2` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段2',
  `field3` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段3',
  `field4` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段4',
  `field5` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段5',
  `field6` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段6',
  `field7` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段7',
  `field8` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段8',
  `field9` longtext COLLATE utf8mb4_unicode_ci COMMENT '扩展字段9',
  PRIMARY KEY (`id`),
  UNIQUE KEY `solrid` (`solrid`),
  KEY `idx_spider_name` (`spider_name`),
  KEY `idx_parseflag` (`parseflag`),
  KEY `idx_url` (`url`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""
