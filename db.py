"""
数据库模块 - SQLite 用户系统、学情记录、聊天消息管理
"""
import sqlite3
import json
import os
import hashlib
from datetime import datetime
from typing import List, Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "learning_data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'student')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 习题表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER REFERENCES users(id),
            question TEXT NOT NULL,
            standard_answer_points TEXT NOT NULL,
            total_max_score REAL DEFAULT 15,
            pdf_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 答题记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER REFERENCES users(id),
            student_name TEXT DEFAULT '匿名学生',
            exercise_id INTEGER REFERENCES exercises(id),
            question TEXT NOT NULL,
            standard_answer_points TEXT NOT NULL,
            student_answer TEXT NOT NULL,
            step_scores TEXT,
            logic_score REAL,
            total_score REAL,
            feedback TEXT,
            weak_tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 知识点统计表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT UNIQUE NOT NULL,
            error_count INTEGER DEFAULT 0
        )
    """)

    # 聊天消息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES users(id),
            receiver_id INTEGER NOT NULL REFERENCES users(id),
            content TEXT DEFAULT '',
            file_path TEXT DEFAULT '',
            file_name TEXT DEFAULT '',
            file_type TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# 用户管理
# ============================================================
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str, role: str) -> tuple[bool, str]:
    """注册用户，返回 (成功, 消息)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, _hash_password(password), role),
        )
        conn.commit()
        return True, "注册成功"
    except sqlite3.IntegrityError:
        return False, "用户名已存在"
    finally:
        conn.close()


def login_user(username: str, password: str) -> Optional[dict]:
    """登录验证，成功返回用户信息字典，失败返回 None"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, _hash_password(password)),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_teacher_id() -> Optional[int]:
    """获取系统中第一个教师的ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE role = 'teacher' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None


def get_all_students() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM users WHERE role = 'student' ORDER BY username")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_teachers() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM users WHERE role = 'teacher' ORDER BY username")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_last_message_between(user_id_1: int, user_id_2: int) -> Optional[dict]:
    """获取两个用户之间的最后一条消息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at DESC LIMIT 1""",
        (user_id_1, user_id_2, user_id_2, user_id_1),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# 习题管理
# ============================================================
def save_exercise(teacher_id: int, question: str, standard_answer_points: str,
                  total_max_score: float, pdf_source: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO exercises (teacher_id, question, standard_answer_points, total_max_score, pdf_source) VALUES (?, ?, ?, ?, ?)",
        (teacher_id, question, standard_answer_points, total_max_score, pdf_source),
    )
    eid = cursor.lastrowid
    conn.commit()
    conn.close()
    return eid


def get_all_exercises() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exercises ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_exercise_by_id(exercise_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# 答题记录
# ============================================================
def save_exam_record(question: str, standard_answer_points: str, student_answer: str,
                     grading_result: dict, student_name: str = "匿名学生",
                     student_id: int = None, exercise_id: int = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO exam_records
        (student_id, student_name, exercise_id, question, standard_answer_points,
         student_answer, step_scores, logic_score, total_score, feedback, weak_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            student_id, student_name, exercise_id,
            question, standard_answer_points, student_answer,
            json.dumps(grading_result.get("step_scores", []), ensure_ascii=False),
            grading_result.get("logic_score", 0),
            grading_result.get("total_score", 0),
            grading_result.get("feedback", ""),
            json.dumps(grading_result.get("weak_tags", []), ensure_ascii=False),
        ),
    )
    weak_tags = grading_result.get("weak_tags", [])
    for tag in weak_tags:
        cursor.execute(
            "INSERT INTO knowledge_tags (tag_name, error_count) VALUES (?, 1) "
            "ON CONFLICT(tag_name) DO UPDATE SET error_count = error_count + 1",
            (tag,),
        )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_student_records(student_id: int, limit: int = 50) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM exam_records WHERE student_id = ? ORDER BY created_at DESC LIMIT ?",
        (student_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_exam_records(limit: int = 50) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exam_records ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_error_statistics() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tag_name, error_count FROM knowledge_tags ORDER BY error_count DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"tag": row["tag_name"], "count": row["error_count"]} for row in rows]


def get_student_error_statistics(student_id: int) -> List[dict]:
    """获取某个学生的薄弱知识点统计"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT weak_tags FROM exam_records WHERE student_id = ?", (student_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    tag_counts = {}
    for row in rows:
        tags = json.loads(row["weak_tags"]) if row["weak_tags"] else []
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return [{"tag": k, "count": v} for k, v in sorted(tag_counts.items(), key=lambda x: -x[1])]


def get_total_exam_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_records")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ============================================================
# 聊天消息
# ============================================================
def send_message(sender_id: int, receiver_id: int, content: str = "",
                 file_path: str = "", file_name: str = "", file_type: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender_id, receiver_id, content, file_path, file_name, file_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (sender_id, receiver_id, content, file_path, file_name, file_type),
    )
    mid = cursor.lastrowid
    conn.commit()
    conn.close()
    return mid


def get_messages(user_id_1: int, user_id_2: int, limit: int = 100) -> List[dict]:
    """获取两个用户之间的所有消息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT m.*, u.username as sender_name FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC LIMIT ?""",
        (user_id_1, user_id_2, user_id_2, user_id_1, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unread_count(user_id: int, sender_id: int, since_id: int = 0) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM messages WHERE sender_id = ? AND receiver_id = ? AND id > ?",
        (sender_id, user_id, since_id),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count
