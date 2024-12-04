import sys, backup_db
args = sys.argv

if (__name__ == '__main__') and (len(args) >=2):
    # 引き数"args[1]"により実行関数を指定している
    match args[1]:
        case "cp": # DBファイルのコピーバックアップ
            backup_db.copy_db_file()
        case "tUser": # usersテーブルのCSV形式でバックアップ
            backup_db.export_table_csv("users", "users")
        case "tAttendance": # usersテーブルのCSV形式でバックアップ
            backup_db.export_table_csv("attendance", "stamps")
        case "attendanceView": # 出退勤履歴集計のCSV形式でバックアップ
            backup_db.export_attendance_view()
