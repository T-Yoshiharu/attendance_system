from flask import Flask, render_template, request, redirect, url_for, session, has_request_context
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from admin_services import DiscordHandler
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッション管理のためのシークレットキー

with open("id.json", "r") as f:
    ids = json.load(f)


# Discordへのログ出力
webhook_url = ids["Discord"]
# Discord Handler の作成
discord_handler = DiscordHandler(webhook_url)
discord_handler.setLevel(logging.INFO)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(discord_handler)

# コンソールのログ出力
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
werkzeug_logger.addHandler(console_handler)


# レート制限のデフォルト設定
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "120 per hour"],
    storage_uri="memory://",
)


# データベース接続
def connect_db():
    return sqlite3.connect('attendance.db')

# テーブル作成（初回のみ）
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    # ユーザーテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            content TEXT,
            io INTEGER,
            is_admin INTEGER DEFAULT 0
        )
    ''')

    # 出退勤テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            check_in_time TEXT,
            check_out_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# ログイン処理
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        # パスワードチェック
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = username
            session['is_admin'] = user[5]  # 管理者フラグをセッションに保存
            return redirect(url_for('index'))
        else:
            return 'ユーザー名またはパスワードが無効です'

    return render_template('login.html')

# 出勤・退勤打刻
@app.route('/', methods=['POST'])
@limiter.limit("1 per minute")
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username')

    if request.method == 'POST':
        action = request.form['action']
        conn = connect_db()
        cursor = conn.cursor()

        # 現在のタイムスタンプを取得し"YY/MM/DD HH:MM:SS"の形式にする
        now = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        timestamp = datetime.strptime(now, '%Y/%m/%d %H:%M:%S')

        if action == 'check_in':
            cursor.execute('INSERT INTO attendance (user_id, check_in_time) VALUES (?, ?)', (user_id, timestamp))
        elif action == 'check_out':
            cursor.execute('UPDATE attendance SET check_out_time = ? WHERE user_id = ? AND check_out_time IS NULL',
                           (timestamp, user_id))

        conn.commit()
        conn.close()

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT check_in_time, check_out_time FROM attendance WHERE user_id = ? ORDER BY id DESC LIMIT 1',
                   (user_id,))
    attendance = cursor.fetchone()
    conn.close()

    working_hours = None
    if attendance and attendance[0] and attendance[1]:
        check_in_time = datetime.fromisoformat(attendance[0])
        check_out_time = datetime.fromisoformat(attendance[1])
        working_hours = check_out_time - check_in_time

    return render_template('index.html', attendance=attendance, working_hours=working_hours, username=username)

# ホーム画面の表示
@app.route('/', methods=['GET'])
def get_index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username')

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT check_in_time, check_out_time FROM attendance WHERE user_id = ? ORDER BY id DESC LIMIT 1',
                   (user_id,))
    attendance = cursor.fetchone()
    conn.close()

    working_hours = None
    if attendance and attendance[0] and attendance[1]:
        check_in_time = datetime.fromisoformat(attendance[0])
        check_out_time = datetime.fromisoformat(attendance[1])
        working_hours = check_out_time - check_in_time

    return render_template('index.html', attendance=attendance, working_hours=working_hours, username=username)

# ユーザーおよび管理者の退勤履歴を表示
@app.route('/history', methods=['GET'])
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    is_admin = session.get('is_admin', 0)

    conn = connect_db()
    cursor = conn.cursor()

    if is_admin:
        # 管理者の場合、全ユーザーの履歴を取得
        cursor.execute('''
            SELECT u.username, a.check_in_time, a.check_out_time 
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.check_in_time DESC
        ''')
    else:
        # 一般ユーザーの場合、自分の履歴のみ取得
        cursor.execute('''
            SELECT u.username, a.check_in_time, a.check_out_time
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.user_id = ?
            ORDER BY a.check_in_time DESC
        ''', (user_id,))

    records = cursor.fetchall()
    conn.close()

    return render_template('history.html', records=records)

# ユーザー登録
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return 'このユーザー名は既に使われています。'

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', (username, hashed_password, 0))

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# ログアウト処理
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('login'))

# パスワードの変更
@app.route('/changepass', methods=['GET', 'POST'])
def changepass():
    username = session.get('username')
    if request.method == 'POST':
        nowPass = request.form['current_password']
        newPass1 = request.form['new_password']
        newPass2 = request.form['confirm_password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        # パスワードチェック
        if user and check_password_hash(user[2], nowPass):
            if newPass1 == newPass2:
                # 新しいパスワードのハッシュ化
                hashed_password = generate_password_hash(newPass1, method='pbkdf2:sha256')
                # パスワードの書き換え
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user[0]))
                conn.commit()
        else:
            return '現在のパスワードが無効です'

        conn.close()

        return redirect(url_for('index'))

    return render_template('changepass.html')

if __name__ == '__main__':
    create_tables()  # テーブル作成
    app.run(host='0.0.0.0', port=5000, debug=True)
