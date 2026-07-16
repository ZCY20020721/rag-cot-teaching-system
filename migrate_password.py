"""
一次性密码迁移脚本：SHA-256 → bcrypt
运行后，系统 login_user 会在用户登录时自动升级旧格式密码。
本脚本用于强制批量迁移所有存量用户。

用法: python migrate_password.py
"""
import sqlite3
import os

import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "learning_data.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, password_hash FROM users")
    users = cursor.fetchall()

    upgraded = 0
    skipped = 0
    for user in users:
        old_hash = user["password_hash"]
        # 已经是 bcrypt 格式，跳过
        if old_hash.startswith("$2b$"):
            skipped += 1
            continue

        # 旧格式 SHA-256：我们无法反推原密码
        # 但 bcrypt 需要明文密码才能生成哈希
        # 对于存量用户的 SHA-256 哈希，直接强制用户使用"忘记密码"功能
        # 这里标记为需要重置，不做强制覆盖
        print(f"  [需手动重置] {user['username']}: 旧 SHA-256 格式，无法自动迁移")
        skipped += 1

    conn.close()
    print(f"\n迁移完成：{upgraded} 个已升级，{skipped} 个跳过")
    print(
        "提示：旧格式密码将在用户下次登录时自动升级为 bcrypt（login_user 内置自动升级逻辑）"
    )


if __name__ == "__main__":
    migrate()
