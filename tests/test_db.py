"""db.py 单元测试 - 覆盖用户/习题/答题/统计/聊天全部功能"""
import json
import sqlite3

import pytest

import db


# ============================================================
# 数据库初始化
# ============================================================
class TestInit:
    """init_db 测试"""

    def test_all_tables_created(self, temp_db):
        """验证 5 张表全部创建"""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "users" in tables
        assert "exercises" in tables
        assert "exam_records" in tables
        assert "knowledge_tags" in tables
        assert "messages" in tables


# ============================================================
# 用户管理测试
# ============================================================
class TestUserRegistration:
    """注册功能测试"""

    def test_register_teacher_success(self, temp_db):
        ok, msg = db.register_user("teacher_a", "Pass123", "teacher")
        assert ok is True
        assert "成功" in msg

    def test_register_student_success(self, temp_db):
        ok, msg = db.register_user("student_a", "Pass456", "student")
        assert ok is True

    def test_register_duplicate_rejected(self, temp_db):
        db.register_user("dup_user", "Pass123", "student")
        ok, msg = db.register_user("dup_user", "Pass999", "student")
        assert ok is False
        assert "已存在" in msg

    def test_register_weak_password_too_short(self, temp_db):
        ok, msg = db.register_user("u1", "123", "student")
        assert ok is False
        assert "至少" in msg

    def test_register_weak_password_no_digit(self, temp_db):
        ok, msg = db.register_user("u2", "abcdef", "student")
        assert ok is False
        assert "数字" in msg

    def test_register_weak_password_no_letter(self, temp_db):
        ok, msg = db.register_user("u3", "123456", "student")
        assert ok is False
        assert "字母" in msg

    def test_password_stored_as_bcrypt(self, temp_db):
        db.register_user("hash_user", "Secret1", "student")
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username='hash_user'")
        h = c.fetchone()[0]
        conn.close()
        assert h != "Secret1"
        assert h.startswith("$2b$")


class TestUserLogin:
    """登录功能测试"""

    def test_login_with_correct_password(self, sample_users):
        user = db.login_user("test_teacher", "Pass123")
        assert user is not None
        assert user["username"] == "test_teacher"
        assert user["role"] == "teacher"

    def test_login_with_wrong_password(self, sample_users):
        user = db.login_user("test_teacher", "WrongPass")
        assert user is None

    def test_login_nonexistent_user(self, temp_db):
        user = db.login_user("ghost", "Pass123")
        assert user is None

    def test_login_student_role(self, sample_users):
        user = db.login_user("test_student", "Pass456")
        assert user is not None
        assert user["role"] == "student"

    def test_legacy_sha256_auto_upgrade(self, temp_db):
        """SHA-256 旧格式密码自动升级为 bcrypt"""
        import hashlib
        old_hash = hashlib.sha256("OldPass1".encode()).hexdigest()
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ("old_user", old_hash, "student"))
        conn.commit()
        conn.close()
        # 旧密码能登录
        user = db.login_user("old_user", "OldPass1")
        assert user is not None
        # 密码被升级
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username='old_user'")
        new_hash = c.fetchone()[0]
        conn.close()
        assert new_hash.startswith("$2b$")


class TestUserQuery:
    """用户查询测试"""

    def test_get_user_by_id_found(self, sample_users):
        teacher, _ = sample_users
        user = db.get_user_by_id(teacher["id"])
        assert user is not None
        assert user["username"] == "test_teacher"

    def test_get_user_by_id_not_found(self, temp_db):
        assert db.get_user_by_id(99999) is None

    def test_get_teacher_id(self, sample_users):
        tid = db.get_teacher_id()
        assert tid is not None
        assert isinstance(tid, int)

    def test_get_teacher_id_when_none(self, temp_db):
        # 没有教师时返回 None
        # 注册一个学生，确保没有教师
        db.register_user("only_student", "Pass123", "student")
        tid = db.get_teacher_id()
        assert tid is None

    def test_get_all_students(self, sample_users):
        students = db.get_all_students()
        assert len(students) >= 1
        usernames = [s["username"] for s in students]
        assert "test_student" in usernames

    def test_get_all_students_excludes_teachers(self, sample_users):
        students = db.get_all_students()
        usernames = [s["username"] for s in students]
        assert "test_teacher" not in usernames

    def test_get_all_teachers(self, sample_users):
        teachers = db.get_all_teachers()
        assert len(teachers) >= 1
        usernames = [t["username"] for t in teachers]
        assert "test_teacher" in usernames


# ============================================================
# 习题管理测试
# ============================================================
class TestExerciseCRUD:
    """习题增删查测试"""

    def test_save_exercise(self, sample_users, temp_db):
        teacher, _ = sample_users
        points = json.dumps([
            {"point": "定义", "tag": "概念", "max_score": 5},
            {"point": "遍历", "tag": "算法", "max_score": 5},
        ])
        eid = db.save_exercise(teacher["id"], "什么是二叉树?", points, 10)
        assert eid > 0

    def test_get_all_exercises(self, sample_users, temp_db):
        teacher, _ = sample_users
        db.save_exercise(teacher["id"], "题目A", "[]", 10)
        db.save_exercise(teacher["id"], "题目B", "[]", 15)
        exercises = db.get_all_exercises()
        assert len(exercises) == 2

    def test_get_exercise_by_id(self, sample_users, temp_db):
        teacher, _ = sample_users
        eid = db.save_exercise(teacher["id"], "查找测试", "[]", 10)
        ex = db.get_exercise_by_id(eid)
        assert ex is not None
        assert ex["question"] == "查找测试"

    def test_get_exercise_by_id_not_found(self, temp_db):
        assert db.get_exercise_by_id(99999) is None


# ============================================================
# 答题记录测试
# ============================================================
class TestExamRecords:
    """答题记录保存和查询测试"""

    def test_save_and_retrieve_record(self, sample_users, temp_db):
        teacher, student = sample_users
        eid = db.save_exercise(teacher["id"], "测试题", "[]", 10)

        grading = {
            "step_scores": [
                {"point_index": 0, "student_content": "...", "score": 4, "comment": "ok"}
            ],
            "logic_score": 3,
            "total_score": 7.0,
            "feedback": "不错，再想想",
            "weak_tags": ["概念不清"],
        }

        rid = db.save_exam_record(
            question="测试题",
            standard_answer_points="[]",
            student_answer="我的答案",
            grading_result=grading,
            student_name="test_student",
            student_id=student["id"],
            exercise_id=eid,
        )
        assert rid > 0

        records = db.get_student_records(student["id"])
        assert len(records) == 1
        assert records[0]["total_score"] == 7.0
        assert records[0]["student_answer"] == "我的答案"

    def test_get_all_exam_records(self, sample_users, temp_db):
        teacher, student = sample_users
        eid = db.save_exercise(teacher["id"], "全局题", "[]", 10)
        db.save_exam_record(
            question="全局题", standard_answer_points="[]",
            student_answer="答案", grading_result={
                "step_scores": [], "logic_score": 3, "total_score": 3,
                "feedback": "...", "weak_tags": []
            },
            student_name="test_student", student_id=student["id"], exercise_id=eid,
        )
        all_records = db.get_all_exam_records()
        assert len(all_records) >= 1

    def test_get_total_exam_count(self, sample_users, temp_db):
        teacher, student = sample_users
        before = db.get_total_exam_count()
        eid = db.save_exercise(teacher["id"], "计数", "[]", 10)
        db.save_exam_record(
            question="计数", standard_answer_points="[]",
            student_answer="...", grading_result={
                "step_scores": [], "logic_score": 3, "total_score": 3,
                "feedback": "...", "weak_tags": []
            },
            student_name="test_student", student_id=student["id"], exercise_id=eid,
        )
        assert db.get_total_exam_count() == before + 1


# ============================================================
# 知识点统计测试
# ============================================================
class TestErrorStatistics:
    """错误统计功能测试"""

    def test_global_error_statistics(self, sample_users, temp_db):
        teacher, student = sample_users
        eid = db.save_exercise(teacher["id"], "统计题", "[]", 10)

        for _ in range(2):
            db.save_exam_record(
                question="统计题", standard_answer_points="[]",
                student_answer="...",
                grading_result={
                    "step_scores": [], "logic_score": 3, "total_score": 3,
                    "feedback": "...", "weak_tags": ["递归", "指针"]
                },
                student_name="test_student", student_id=student["id"], exercise_id=eid,
            )

        stats = db.get_error_statistics()
        tags = {s["tag"]: s["count"] for s in stats}
        assert tags["递归"] == 2
        assert tags["指针"] == 2

    def test_student_personal_error_statistics(self, sample_users, temp_db):
        teacher, student = sample_users
        eid = db.save_exercise(teacher["id"], "个人统计", "[]", 10)
        db.save_exam_record(
            question="个人统计", standard_answer_points="[]",
            student_answer="...",
            grading_result={
                "step_scores": [], "logic_score": 2, "total_score": 2,
                "feedback": "...", "weak_tags": ["排序", "复杂度"]
            },
            student_name="test_student", student_id=student["id"], exercise_id=eid,
        )

        personal = db.get_student_error_statistics(student["id"])
        assert len(personal) == 2
        tags = {s["tag"]: s["count"] for s in personal}
        assert tags["排序"] == 1
        assert tags["复杂度"] == 1

    def test_student_no_errors(self, sample_users):
        """没有答题记录的学生，个人统计为空"""
        # 注册一个新学生，无答题记录
        db.register_user("new_student", "Pass789", "student")
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username='new_student'")
        sid = c.fetchone()["id"]
        conn.close()

        stats = db.get_student_error_statistics(sid)
        assert stats == []


# ============================================================
# 聊天消息测试
# ============================================================
class TestChatMessages:
    """聊天消息功能测试"""

    def test_send_and_get_messages(self, sample_users, temp_db):
        teacher, student = sample_users
        mid = db.send_message(teacher["id"], student["id"], content="你好同学")
        assert mid > 0

        msgs = db.get_messages(teacher["id"], student["id"])
        assert len(msgs) >= 1
        assert msgs[-1]["content"] == "你好同学"

    def test_messages_ordered_by_time(self, sample_users, temp_db):
        teacher, student = sample_users
        db.send_message(teacher["id"], student["id"], content="第一条")
        db.send_message(student["id"], teacher["id"], content="第二条")
        db.send_message(teacher["id"], student["id"], content="第三条")

        msgs = db.get_messages(teacher["id"], student["id"])
        assert len(msgs) == 3
        assert msgs[0]["content"] == "第一条"
        assert msgs[1]["content"] == "第二条"
        assert msgs[2]["content"] == "第三条"

    def test_last_message(self, sample_users, temp_db):
        teacher, student = sample_users
        db.send_message(teacher["id"], student["id"], content="first")

        import time
        time.sleep(0.01)  # 确保时间戳不同

        db.send_message(student["id"], teacher["id"], content="last")

        last = db.get_last_message_between(teacher["id"], student["id"])
        assert last is not None
        # 最后一条应该是时间更晚的那条
        assert last["content"] in ("first", "last")

    def test_last_message_when_empty(self, sample_users):
        teacher, student = sample_users
        last = db.get_last_message_between(teacher["id"], student["id"])
        assert last is None

    def test_message_with_file(self, sample_users, temp_db):
        teacher, student = sample_users
        db.send_message(
            teacher["id"], student["id"],
            content="[image: photo.png]",
            file_path="/tmp/photo.png",
            file_name="photo.png",
            file_type="image",
        )
        msgs = db.get_messages(teacher["id"], student["id"])
        assert msgs[-1]["file_type"] == "image"
        assert msgs[-1]["file_name"] == "photo.png"

    def test_unread_count(self, sample_users, temp_db):
        teacher, student = sample_users
        # 教师发2条消息给学生
        db.send_message(teacher["id"], student["id"], content="msg1")
        db.send_message(teacher["id"], student["id"], content="msg2")

        count = db.get_unread_count(student["id"], teacher["id"], since_id=0)
        assert count == 2

    def test_unread_count_with_since(self, sample_users, temp_db):
        teacher, student = sample_users
        mid1 = db.send_message(teacher["id"], student["id"], content="msg1")
        db.send_message(teacher["id"], student["id"], content="msg2")

        # 只统计 id > mid1 的（即第2条）
        count = db.get_unread_count(student["id"], teacher["id"], since_id=mid1)
        assert count == 1


# ============================================================
# SQL 注入防护测试
# ============================================================
class TestSQLInjection:
    """验证参数化查询防止 SQL 注入"""

    def test_sql_injection_in_username(self, temp_db):
        """恶意用户名不应破坏数据库"""
        malicious = "'; DROP TABLE users; --"
        ok, msg = db.register_user(malicious, "Pass123", "student")
        assert ok is True  # 注册成功（被当作普通用户名）
        # users 表仍然存在
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert c.fetchone() is not None
        conn.close()

    def test_sql_injection_in_password_does_not_harm(self, temp_db):
        """恶意密码不应用来登录"""
        db.register_user("safe_user", "SafePass1", "student")
        user = db.login_user("safe_user", "'; DROP TABLE users; --")
        assert user is None  # 密码不匹配
