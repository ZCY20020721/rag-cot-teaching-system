"""pytest 配置文件 - 提供共享 fixtures"""
import os
import sys
import tempfile

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


@pytest.fixture
def temp_db():
    """创建临时数据库，测试结束后自动删除"""
    original_path = db.DB_PATH
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.DB_PATH = tmp_path
    db.init_db()
    yield tmp_path
    # 清理
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    db.DB_PATH = original_path


@pytest.fixture
def sample_users(temp_db):
    """注册一个教师和一个学生，返回 (teacher, student)"""
    ok_t, msg_t = db.register_user("test_teacher", "Pass123", "teacher")
    ok_s, msg_s = db.register_user("test_student", "Pass456", "student")
    assert ok_t and ok_s, f"fixture setup failed: {msg_t}, {msg_s}"

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = 'test_teacher'")
    teacher = dict(cursor.fetchone())
    cursor.execute("SELECT * FROM users WHERE username = 'test_student'")
    student = dict(cursor.fetchone())
    conn.close()
    return teacher, student
