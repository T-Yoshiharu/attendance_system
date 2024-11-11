from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッション管理のためのシークレットキー

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
            session['is_admin'] = user[3]  # 管理者フラグをセッションに保存
            return redirect(url_for('index'))
        else:
            return 'ユーザー名またはパスワードが無効です'

    return render_template('login.html')

# 出勤・退勤打刻
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username')

    if request.method == 'POST':
        action = request.form['action']
        conn = connect_db()
        cursor = conn.cursor()

        if action == 'check_in':
            cursor.execute('INSERT INTO attendance (user_id, check_in_time) VALUES (?, ?)', (user_id, datetime.now()))
        elif action == 'check_out':
            cursor.execute('UPDATE attendance SET check_out_time = ? WHERE user_id = ? AND check_out_time IS NULL',
                           (datetime.now(), user_id))

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
        working_hours = (check_out_time - check_in_time).total_seconds() / 3600

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

if __name__ == '__main__':
    create_tables()  # テーブル作成
    app.run(host='0.0.0.0', port=5000, debug=True)
