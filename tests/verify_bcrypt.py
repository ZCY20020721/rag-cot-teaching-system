"""bcrypt 升级快速验证脚本"""
import os
import sys
import tempfile
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['TESTING'] = '1'

import db

# 用临时数据库测试
orig_path = db.DB_PATH
fd, tmp = tempfile.mkstemp(suffix='.db')
os.close(fd)
db.DB_PATH = tmp
db.init_db()

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name}")
        failed += 1

# === Test 1: bcrypt format ===
print("Test 1: bcrypt password format")
ok, msg = db.register_user('teacher1', 'Pass123', 'teacher')
check("register teacher", ok)

conn = db.get_connection()
c = conn.cursor()
c.execute('SELECT password_hash FROM users WHERE username=?', ('teacher1',))
row = c.fetchone()
conn.close()
check("password is bcrypt format", row[0].startswith('$2b$'))

# === Test 2: weak password rejection ===
print("\nTest 2: weak password rejection")
check("too short (3)", not db.register_user('u1', '123', 'student')[0])
check("no digit (6)", not db.register_user('u2', 'abcdef', 'student')[0])
check("no letter (6)", not db.register_user('u3', '123456', 'student')[0])

# === Test 3: login with correct password ===
print("\nTest 3: login with correct password")
user = db.login_user('teacher1', 'Pass123')
check("login success", user is not None)
check("correct role", user and user['role'] == 'teacher')

# === Test 4: login with wrong password ===
print("\nTest 4: login with wrong password")
check("wrong password rejected", db.login_user('teacher1', 'WrongPass') is None)

# === Test 5: SHA-256 auto-upgrade ===
print("\nTest 5: SHA-256 legacy auto-upgrade")
old_hash = hashlib.sha256('OldPass1'.encode()).hexdigest()
conn = db.get_connection()
c = conn.cursor()
c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
          ('old_user', old_hash, 'student'))
conn.commit()
conn.close()

user = db.login_user('old_user', 'OldPass1')
check("legacy login success", user is not None)

conn = db.get_connection()
c = conn.cursor()
c.execute('SELECT password_hash FROM users WHERE username=?', ('old_user',))
row = c.fetchone()
conn.close()
check("auto-upgraded to bcrypt", row[0].startswith('$2b$'))

# === Test 6: duplicate username ===
print("\nTest 6: duplicate username rejection")
ok, msg = db.register_user('teacher1', 'Pass999', 'teacher')
check("duplicate rejected", not ok)

# === Cleanup ===
os.unlink(tmp)

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"FAILED {failed} test(s)!")
