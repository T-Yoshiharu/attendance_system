from flask import Flask, render_template, request, redirect, url_for, session, has_request_context
from datetime import datetime
import sqlite3, logging, json, sys, pathlib
from werkzeug.security import generate_password_hash, check_password_hash
from admin_services import DiscordHandler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from LINE.App_LINE import post
from admin.edit_db import readSQL

# 親ディレクトリの設定(Yt24_attendance)
parent_dir = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(parent_dir)

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
            location TEXT REFERENCES locations(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY,
            location_name TEXT NOT NULL
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
    action = request.form['action']

    # 現在のタイムスタンプを取得し"YY/MM/DD HH:MM:SS"の形式にする
    now = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    timestamp = datetime.strptime(now, '%Y/%m/%d %H:%M:%S')

    # ユーザー名取得
    name_o = readSQL(f"SELECT username FROM users WHERE id = {user_id}")
    name = name_o[0][0]

    conn = connect_db()
    cursor = conn.cursor()

    if action == 'check_in':
        location = request.form["location"]
        cursor.execute('INSERT INTO attendance (user_id, check_in_time, location) VALUES (?, ?, ?)', (user_id, timestamp, location))
        if location == "315": # 315の出勤をLINEへ送信
            post(name, "checkIN")
    elif action == 'check_out': # 当日分のみ退勤打刻可とする
        cursor.execute('SELECT id, check_in_time FROM attendance WHERE user_id = ? AND check_out_time IS NULL ORDER BY id DESC LIMIT 1', (user_id,))
        latest = cursor.fetchall()

        if latest:
            for i in latest:
                latest_date = datetime.fromisoformat(i[1]).date()
                if latest_date == timestamp.date():
                    cursor.execute('UPDATE attendance SET check_out_time = ? WHERE id = ? AND check_out_time IS NULL',
                                (timestamp, i[0]))
                    cursor.execute("SELECT location FROM attendance WHERE id = ?", (i[0],))
                    location = cursor.fetchone()[0]
                    if location == "315": # 315の退勤をLINEへ送信
                        post(name, "checkOUT")
                    break
                return "打刻可能な出勤履歴がありません"
        else:
            return "打刻可能な出勤履歴がありません"

    conn.commit()
    conn.close()

    return redirect(url_for("get_index")) #GETメソッドへのリダイレクト（POSTの再送防止）

# ホーム画面の表示
@app.route('/', methods=['GET'])
def get_index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username')
    is_checkout = True # 退勤フラグ(デフォルトTrue)
    now = datetime.now().date()

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT check_in_time, check_out_time FROM attendance WHERE user_id = ? ORDER BY id DESC LIMIT 1',
                   (user_id,))
    attendance = cursor.fetchone()
    cursor.execute('SELECT * FROM locations')
    location = cursor.fetchall()
    conn.close()

    working_hours = None

    if attendance:
        # 退勤状態の判定とフラグの設定
        date = datetime.fromisoformat(attendance[0]).date()
        if (date == now) and (not attendance[1]):
            is_checkout = False

        if attendance[0] and attendance[1]:
            check_in_time = datetime.fromisoformat(attendance[0])
            check_out_time = datetime.fromisoformat(attendance[1])
            working_hours = check_out_time - check_in_time

    return render_template('index.html', attendance=attendance, working_hours=working_hours, username=username, location=location, is_checkout=is_checkout, time=now)


# ユーザーの出退勤履歴を表示（一般ユーザーモード）
@app.route('/history', methods=['GET'])
def history_defalt():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    admin = False
    is_admin = session.get('is_admin', 0)
    if is_admin:
        admin = True

    records = get_history(0, user_id)

    return render_template('history.html', records=records, isAdmin = admin)


# 全ユーザーの出退勤履歴を表示（管理者モード）
@app.route('/admin_history', methods=['GET'])
def history_admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    is_admin = session.get('is_admin', 0)

    if is_admin:
        records = get_history(1)
        return render_template('admin_history.html', records=records)
    else:
        return redirect(url_for("history_defalt"))


# 出退勤の打刻履歴をDBから取得する
def get_history(mode:int, u_id:str = ""):
    conn = connect_db()
    cursor = conn.cursor()

    match mode:
        case 1: # 管理者の場合、全ユーザーの履歴を取得
            cursor.execute('''
            SELECT u.username, a.check_in_time, a.check_out_time, l.location_name
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            JOIN locations l ON a.location = l.id
            ORDER BY a.check_in_time DESC
        ''')
        case 0: # 一般ユーザーの場合、自分の履歴のみ取得
            cursor.execute('''
            SELECT u.username, a.check_in_time, a.check_out_time, l.location_name
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            JOIN locations l ON a.location = l.id
            WHERE a.user_id = ?
            ORDER BY a.check_in_time DESC
        ''', (u_id,))

    out = cursor.fetchall()
    conn.close()

    return out


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

# 出勤中ユーザーの一覧表示
@app.route("/working_staff", methods=['GET'])
def isWorking():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = datetime.now().strftime('%Y-%m-%d')

    # 出勤中のユーザー情報を取得
    sql = f"SELECT u.username, u.content, u.io, a.check_in_time FROM attendance a JOIN users u ON a.user_id = u.id WHERE a.check_in_time LIKE '{today}%' AND a.check_out_time IS NULL AND a.location=315"
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(sql)
    working_list = cursor.fetchall()
    conn.close()

    return render_template("working_staff.html", working_list=working_list)


if __name__ == '__main__':
    create_tables()  # テーブル作成
    app.run(host='0.0.0.0', port=5000, debug=True)
