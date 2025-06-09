import sqlite3

# データベースファイルに接続
connection = sqlite3.connect('database.db')

# schema.sqlファイルを開いて読み込む
with open('schema.sql') as f:
    connection.executescript(f.read())

# 変更をコミット（保存）して接続を閉じる
connection.commit()
connection.close()

print("データベースが正常に初期化されました。")