"""Tests for core.alarm_db.AlarmDB."""

import os
import tempfile
import time

import pytest

from core.alarm_db import AlarmDB


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    alarm_db = AlarmDB(path)
    yield alarm_db
    alarm_db.close()
    os.unlink(path)


class TestAlarmDB:
    def test_insert_and_load_today(self, db):
        event = {
            "ts": time.time(),
            "time": "12:30:00",
            "camera": "cam01",
            "level": "confirm",
            "status": "pending",
            "max_conf": 0.85,
            "orig_path": "/tmp/a.jpg",
            "annotated_path": "/tmp/b.jpg",
        }
        row_id = db.insert(event)
        assert row_id is not None
        assert row_id > 0

        records = db.load_today()
        assert len(records) == 1
        assert records[0]["camera"] == "cam01"
        assert records[0]["max_conf"] == 0.85

    def test_insert_multiple(self, db):
        for i in range(5):
            db.insert({
                "ts": time.time() + i,
                "camera": f"cam{i:02d}",
                "level": "warn",
            })
        records = db.load_today()
        assert len(records) == 5

    def test_load_by_date(self, db):
        today = time.strftime("%Y-%m-%d")
        db.insert({"ts": time.time(), "camera": "cam01", "level": "confirm"})
        records = db.load_by_date(today)
        assert len(records) == 1
        # Non-existent date
        records = db.load_by_date("2020-01-01")
        assert len(records) == 0

    def test_load_recent(self, db):
        for i in range(10):
            db.insert({"ts": time.time() + i, "camera": "cam01", "level": "confirm"})
        records = db.load_recent(limit=3)
        assert len(records) == 3

    def test_count_today(self, db):
        assert db.count_today() == 0
        db.insert({"ts": time.time(), "camera": "cam01", "level": "confirm"})
        db.insert({"ts": time.time(), "camera": "cam02", "level": "warn"})
        assert db.count_today() == 2

    def test_update_clip_path(self, db):
        ts = time.time()
        db.insert({
            "ts": ts,
            "camera": "cam01",
            "level": "confirm",
            "clip_path": None,
        })
        db.update_clip_path(ts, "cam01", "/tmp/clip.avi")
        records = db.load_today()
        assert records[0]["clip_path"] == "/tmp/clip.avi"

    def test_get_date_list(self, db):
        db.insert({"ts": time.time(), "camera": "cam01", "level": "confirm"})
        dates = db.get_date_list()
        assert len(dates) >= 1
        assert time.strftime("%Y-%m-%d") in dates

    def test_row_to_dict_fields(self, db):
        db.insert({
            "ts": time.time(),
            "camera": "cam01",
            "level": "spreading",
            "max_conf": 0.92,
        })
        record = db.load_today()[0]
        assert "id" in record
        assert "ts" in record
        assert "camera" in record
        assert "level" in record
        assert "max_conf" in record
        assert "clip_path" in record
