import sys, pathlib, sqlite3
parent_dir = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(parent_dir)

# データベース接続
def connect_db():
    return sqlite3.connect('attendance.db')


# DBへの書き込み
def writeSQL(query: str = None):
    if query == None:
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()

    return "===書き込み成功==="


# DBからの読み込み
def readSQL(query: str = None):
    if query == None:
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query)
    output = cursor.fetchall()
    conn.close()

    return output


if __name__ == '__main__':
    while True:
        func = input("実行する関数名を入力: ")

        if func == "writeSQL":
            query = input("SQLのクエリ文を入力: ")
            log = writeSQL(query)
            print(log)
        elif func == "readSQL":
            query = input("SQLのクエリ文を入力: ")
            ans = readSQL(query)
            # 結果の出力
            for i in ans:
                print(i)
        elif func == "exit":
            print("===終了します===")
            break
        else:
            print("関数名が誤っています")
