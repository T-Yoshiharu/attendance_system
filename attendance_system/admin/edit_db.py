import sys, pathlib
parent_dir = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(parent_dir)
from app import connect_db


# DMへの書き込み
def writeSQL(query: str = None):
    if query == None:
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()

    print("===書き込み成功===")


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
            writeSQL(query)
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
