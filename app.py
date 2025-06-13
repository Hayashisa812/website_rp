from flask import Flask, render_template, request, jsonify, g
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import random
import sqlite3 # sqlite3をインポート

app = Flask(__name__)
socketio = SocketIO(app)

# 変更: データベースファイルの名前を定義
DATABASE = 'database.db'

member_store = {}
sid_to_user = {}


def get_db():
    """リクエスト内で有効なデータベース接続を取得する。なければ作成する。"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # 辞書のように列名でアクセスできるようにする
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """リクエストの終了時にデータベース接続を閉じる。"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/thread/<board_name>')
def thread(board_name):
    return render_template("index.html", board_name=board_name)

@app.route('/messages/<board_name>')
def get_messages(board_name):
    # DBからメッセージを取得
    db = get_db()
    cur = db.execute(
        'SELECT * FROM messages WHERE board_name = ? ORDER BY time ASC', 
        (board_name,)
    )
    messages = [dict(row) for row in cur.fetchall()]
    return jsonify(messages)


@app.route('/reply/<board_name>',methods=['POST'])
def handle_reply(board_name):
    data = request.json
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    # 返信先のIDをテキストに含める
    reply_text = f">> {data['id']}\n{data['text']}"

    # DBにメッセージを挿入
    db = get_db()
    db.execute(
       'INSERT INTO messages (board_name, text, sender, time, reply_to_id) VALUES (?, ?, ?, ?, ?)',
        (board_name, reply_text, data['sender'], current_time, data['id'])
    )
    db.commit()

    # 挿入した最新のメッセージを取得してクライアントに送信
    cur = db.execute('SELECT * FROM messages WHERE id = last_insert_rowid()')
    new_msg = dict(cur.fetchone())

    # 'new_message' イベントとしてブロードキャストする
    socketio.emit('new_message', new_msg, room=board_name)
    return jsonify({'status': 'ok'})


@app.route('/post/<board_name>', methods=['POST'])
def post_message(board_name):
    data = request.json
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    # DBにメッセージを挿入
    db = get_db()
    db.execute(
        'INSERT INTO messages (board_name, text, sender, time) VALUES (?, ?, ?, ?)',
        (board_name, data['text'], data['sender'], current_time)
    )
    db.commit()

    # 挿入した最新のメッセージを取得してクライアントに送信
    cur = db.execute('SELECT * FROM messages WHERE id = last_insert_rowid()')
    new_msg = dict(cur.fetchone())

    # メッセージを特定の掲示板ルームにのみブロードキャストする
    socketio.emit('new_message', new_msg, room=board_name)
    return jsonify({'status': 'ok'})

@app.route('/delete/<board_name>', methods=['POST'])
def delete_message(board_name):
    data = request.json

    # DBからメッセージを削除
    db = get_db()
    db.execute(
        'DELETE FROM messages WHERE id = ? AND sender = ?', 
        (data['id'], data['sender'])
    )
    db.commit()

    # 削除イベントを特定の掲示板ルームにのみブロードキャストする
    socketio.emit('delete_message', data, room=board_name)
    return jsonify({'status': 'deleted'})

@app.route('/reaction/<board_name>', methods=['POST'])
def add_reaction(board_name):
    data = request.json
    random_image = random.choice(["https://cdn-icons-png.flaticon.com/512/833/833472.png","https://cdn-icons-png.flaticon.com/512/2107/2107957.png","https://cdn-icons-png.flaticon.com/512/2107/2107932.png","https://cdn-icons-png.flaticon.com/512/742/742751.png","https://cdn-icons-png.flaticon.com/512/3075/3075977.png","https://cdn-icons-png.flaticon.com/512/2278/2278992.png"])
    msg = {
        'reaction': random_image,
        'id': data['id'],
    }
    # リアクションイベントを特定の掲示板ルームにのみブロードキャストする
    socketio.emit('reaction', msg, room=board_name)
    return jsonify({'status': 'ok'})

@socketio.on('join')
def handle_join(data):
    board_name = data['board']
    sender_id = data['sender']
    
    join_room(board_name)
    
    sid_to_user[request.sid] = {'board': board_name, 'sender': sender_id}
    
    member_store.setdefault(board_name, set()).add(sender_id)
    
    # setをリストに変換して送信
    emit('member_update', {'members': list(member_store.get(board_name, []))}, room=board_name)
    print(f"User {sender_id} joined {board_name}. Current members: {list(member_store.get(board_name, []))}")


@socketio.on('disconnect')#切断時の実行
def handle_disconnect():
    user_info = sid_to_user.pop(request.sid, None)
    
    if user_info:
        board_name = user_info['board']
        sender_id = user_info['sender']
        leave_room(board_name)
        
        if board_name in member_store and sender_id in member_store[board_name]:
            member_store[board_name].remove(sender_id)
            if not member_store[board_name]:
                del member_store[board_name]
        
        emit('member_update', {'members': list(member_store.get(board_name, []))}, room=board_name)
        print(f"User {sender_id} disconnected from {board_name}. Current members: {member_store.get(board_name, [])}")


@app.route('/search/<board_name>', methods=['POST'])
def search_messages(board_name):
    data = request.json

    search_term = f"%{data['text']}%"#DBでLIKE検索を実行

    db = get_db()
    cur = db.execute(
        'SELECT * FROM messages WHERE board_name = ? AND text LIKE ? ORDER BY time ASC',
        (board_name, search_term)
    )
    filtered_messages = [dict(row) for row in cur.fetchall()]
    
    return jsonify({'status': 'ok', 'messages': filtered_messages})

if __name__ == '__main__':
    socketio.run(app, debug=True)