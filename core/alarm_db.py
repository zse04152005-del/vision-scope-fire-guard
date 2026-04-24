"""告警数据库 — SQLite 持久化存储，启动时加载历史记录。"""

import logging
import os
import sqlite3
import time
from typing import Optional

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS alarms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL    NOT NULL,
    time_str    TEXT    NOT NULL,
    date_str    TEXT    NOT NULL,
    camera      TEXT    NOT NULL,
    level       TEXT    NOT NULL DEFAULT 'confirm',
    status      TEXT    NOT NULL DEFAULT 'pending',
    max_conf    REAL    NOT NULL DEFAULT 0.0,
    orig_path   TEXT,
    ann_path    TEXT,
    clip_path   TEXT
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_alarms_ts ON alarms(ts);
CREATE INDEX IF NOT EXISTS idx_alarms_date ON alarms(date_str);
CREATE INDEX IF NOT EXISTS idx_alarms_camera ON alarms(camera);
"""


class AlarmDB:
    """告警事件 SQLite 持久化存储。

    每条告警记录包含时间戳、摄像头、等级、置信度、截图/录像路径。
    支持按日期查询、全量加载、追加写入。
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_CREATE_TABLE + _CREATE_INDEX)
            self._conn.commit()
            logger.info("告警数据库已初始化: %s", self._db_path)
        except Exception as exc:
            logger.error("告警数据库初始化失败: %s", exc)
            self._conn = None

    def insert(self, event: dict) -> Optional[int]:
        """插入一条告警记录，返回记录 ID。"""
        if not self._conn:
            return None
        try:
            ts = event.get("ts", time.time())
            cur = self._conn.execute(
                """INSERT INTO alarms (ts, time_str, date_str, camera, level, status,
                   max_conf, orig_path, ann_path, clip_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ts,
                    event.get("time", time.strftime("%H:%M:%S", time.localtime(ts))),
                    time.strftime("%Y-%m-%d", time.localtime(ts)),
                    event.get("camera", ""),
                    event.get("level", "confirm"),
                    event.get("status", "pending"),
                    float(event.get("max_conf", 0.0)),
                    event.get("orig_path"),
                    event.get("annotated_path"),
                    event.get("clip_path"),
                ),
            )
            self._conn.commit()
            return cur.lastrowid
        except Exception as exc:
            logger.error("插入告警记录失败: %s", exc)
            return None

    def update_clip_path(self, ts: float, camera: str, clip_path: str) -> None:
        """更新告警录像路径（录像异步保存完成后回填）。"""
        if not self._conn:
            return
        try:
            self._conn.execute(
                "UPDATE alarms SET clip_path = ? WHERE camera = ? AND ABS(ts - ?) < 1.0",
                (clip_path, camera, ts),
            )
            self._conn.commit()
        except Exception as exc:
            logger.error("更新录像路径失败: %s", exc)

    def load_today(self) -> list[dict]:
        """加载今天的告警记录。"""
        today = time.strftime("%Y-%m-%d")
        return self.load_by_date(today)

    def load_by_date(self, date_str: str) -> list[dict]:
        """加载指定日期的告警记录。"""
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(
                "SELECT * FROM alarms WHERE date_str = ? ORDER BY ts ASC",
                (date_str,),
            )
            return [self._row_to_dict(row) for row in cur.fetchall()]
        except Exception as exc:
            logger.error("加载告警记录失败: %s", exc)
            return []

    def load_recent(self, limit: int = 10000) -> list[dict]:
        """加载最近 N 条告警记录。"""
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(
                "SELECT * FROM alarms ORDER BY ts DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            return [self._row_to_dict(row) for row in reversed(rows)]
        except Exception as exc:
            logger.error("加载告警记录失败: %s", exc)
            return []

    def count_today(self) -> int:
        """统计今天的告警数。"""
        if not self._conn:
            return 0
        try:
            today = time.strftime("%Y-%m-%d")
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM alarms WHERE date_str = ?", (today,)
            )
            return cur.fetchone()[0]
        except Exception:
            return 0

    def get_date_list(self) -> list[str]:
        """获取所有有记录的日期列表。"""
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(
                "SELECT DISTINCT date_str FROM alarms ORDER BY date_str DESC"
            )
            return [row[0] for row in cur.fetchall()]
        except Exception:
            return []

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        return {
            "id": row[0],
            "ts": row[1],
            "time": row[2],
            "date": row[3],
            "camera": row[4],
            "level": row[5],
            "status": row[6],
            "max_conf": row[7],
            "orig_path": row[8],
            "annotated_path": row[9],
            "clip_path": row[10],
        }

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
