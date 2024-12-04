from datetime import datetime
import csv, subprocess as sub, sys, pathlib
parent_dir = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(parent_dir)
from admin.edit_db import readSQL


# DBファイルのコピー作成
def copy_db_file():
    now = datetime.now().strftime('%Y%m%d-%H%M')
    fname = f"attendance_backup_{now}.db"

    sub.call("cd ~/Yt24_attendance/") #cwdを正す
    sub.call(f"cp attendance.db {fname}") #ファイルをコピーする
    sub.call(f"chmod 544 {fname}") #ファイルが破損しないように権限を変更
    sub.call(f"mv {fname} ~/backup-DB/") #所定の場所にファイルを移動させる


# DBの指定されたテーブルをCSVにして保存
def export_table_csv(table_name: str, dir: str):
    now = datetime.now().strftime('%Y%m%d_%H%M')
    sql1 = f"PRAGMA TABLE_INFO({table_name});"
    sql2 = f"SELECT * FROM {table_name};"
    fname = f"./attendance_system/backupDB/{dir}/{table_name}_{now}.csv"

    # DBからデータ取得
    column = readSQL(sql1) #カラム
    data = readSQL(sql2) #データ

    with open(fname, "w") as f:
        writer = csv.writer(f)

        # カラムの書き込み
        c = []
        for i in column:
            c.append(i[1])
        writer.writerow(c)

        # データの書き込み
        for d in data:
            d = list(d)
            writer.writerow(d)


# DBの出退勤履歴の集計をCSVにして保存
def export_attendance_view():
    now = datetime.now().strftime('%Y%m%d-%H%M')
    sql = '''
            SELECT u.username, a.check_in_time, a.check_out_time, l.location_name
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            JOIN locations l ON a.location = l.id
            ORDER BY a.check_in_time DESC
        '''
    fname = f"./attendance_system/backupDB/attendance_view_{now}.csv"

    data = readSQL(sql) #データ

    with open(fname, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "check_in_time", "check_out_time", "location"])
        # データの書き込み
        for d in data:
            d = list(d)
            writer.writerow(d)
