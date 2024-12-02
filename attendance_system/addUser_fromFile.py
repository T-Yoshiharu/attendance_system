from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3, csv
from app import create_tables, connect_db
from werkzeug.security import generate_password_hash, check_password_hash

# 読み込むCSVファイルのパスを指定
ifile = "./members.csv"


# ユーザー登録
def register(username: str, password:str, content:str, inout: int) -> str:
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return f'{username}は既に使われています。'

    # パスワードのハッシュ化
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    # DBへの登録
    cursor.execute('INSERT INTO users (username, password, content, io, is_admin) VALUES (?, ?, ?, ?, ?)', (username, hashed_password, content, inout, 0))

    conn.commit()
    conn.close()

    return username


if __name__ == '__main__':
    create_tables()
    # ユーザー一括登録(CSVファイルから読み込み)
    with open(ifile, encoding="UTF-8") as data:
        data.readline() # カラム行をスキップ
        reader = csv.reader(data)
        for d in reader:
            result = register(d[0], d[1], d[2], d[3])
            print(result)

        print("===登録完了===")




