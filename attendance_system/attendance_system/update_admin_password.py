import sqlite3
from werkzeug.security import generate_password_hash

# データベースに接続
conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# 管理者のプレーンテキストパスワードをハッシュ化する
# ここでは 'admin_password' がプレーンテキストのパスワードです
hashed_password = generate_password_hash('admin_password', method='pbkdf2:sha256')

# 既存の管理者ユーザーのパスワードをハッシュ化して更新
cursor.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_password, 'admin_user'))

# 変更を保存
conn.commit()
conn.close()

print("管理者パスワードをハッシュ化して更新しました")
