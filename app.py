from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import random

app = Flask(__name__)
socketio = SocketIO(app)

# 掲示板ごとのメッセージ保存
message_store = {}
member_store = {}
# SocketIOのセッションIDとユーザー情報を紐付けるための辞書
sid_to_user = {}

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/thread/<board_name>')
def thread(board_name):
    return render_template("index.html", board_name=board_name)

@app.route('/messages/<board_name>')
def get_messages(board_name):
    return jsonify(message_store.get(board_name, []))

@app.route('/post/<board_name>', methods=['POST'])
def post_message(board_name):
    data = request.json
    msg = {
        'id': len(message_store.get(board_name, [])),
        'text': data['text'],
        'sender': data['sender'],
        'time': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    message_store.setdefault(board_name, []).append(msg)
    socketio.emit('new_message', msg)
    return jsonify({'status': 'ok'})

@app.route('/delete/<board_name>', methods=['POST'])
def delete_message(board_name):
    data = request.json
    messages = message_store.get(board_name, [])
    message_store[board_name] = [
        msg for msg in messages if not (msg['id'] == data['id'] and msg['sender'] == data['sender'])
    ]
    socketio.emit('delete_message', data)
    return jsonify({'status': 'deleted'})
@app.route('/reaction/<board_name>', methods=['POST'])
def add_reaction(board_name):
    data = request.json
    random_image = random.choice(["https://cdn-icons-png.flaticon.com/512/833/833472.png","https://cdn-icons-png.flaticon.com/512/2107/2107957.png","https://cdn-icons-png.flaticon.com/512/2107/2107932.png","https://cdn-icons-png.flaticon.com/512/742/742751.png","https://cdn-icons-png.flaticon.com/512/3075/3075977.png","https://cdn-icons-png.flaticon.com/512/2278/2278992.png"])
    msg = {
        'reaction': random_image,
        'id': data['id'],

    }
    socketio.emit('reaction', msg)
    return jsonify({'status': 'ok'})
@socketio.on('join')
def handle_join(data):
    """クライアントからの参加要求を処理"""
    board_name = data['board']
    sender_id = data['sender']
    
    # ユーザーを特定の掲示板の「ルーム」に参加させる
    join_room(board_name)
    
    # セッションIDとユーザー情報を紐付ける
    sid_to_user[request.sid] = {'board': board_name, 'sender': sender_id}
    
    # メンバーリストに追加
    member_store.setdefault(board_name, []).append(sender_id)
    member_store[board_name] = list(set(member_store[board_name]))
    
    # 同じルームの全員に更新されたメンバーリストを送信
    emit('member_update', {'members': member_store.get(board_name, [])}, room=board_name)
    print(f"User {sender_id} joined {board_name}. Current members: {member_store[board_name]}")


@socketio.on('disconnect')
def handle_disconnect():
    """クライアントの切断を処理"""
    # 切断したクライアントの情報を取得
    user_info = sid_to_user.pop(request.sid, None)
    
    if user_info:
        board_name = user_info['board']
        sender_id = user_info['sender']
        
        # 該当のルームから退出
        leave_room(board_name)
        
        # メンバーリストから削除
        if board_name in member_store and sender_id in member_store[board_name]:
            member_store[board_name].remove(sender_id)
            # もしボードに誰もいなくなったら、そのボードのキーごと削除しても良い
            if not member_store[board_name]:
                del member_store[board_name]
        
        # 同じルームの残りのメンバーに更新されたメンバーリストを送信
        emit('member_update', {'members': member_store.get(board_name, [])}, room=board_name)
        print(f"User {sender_id} disconnected from {board_name}. Current members: {member_store.get(board_name, [])}")


@app.route('/search/<board_name>', methods=['POST'])
def search_messages(board_name):
    print("searching for messages in board:", board_name)
    filtered_messages = []
    data = request.json
    a = message_store.get(board_name,[])
    for i in a:
        if data['text'] in i['text']:
            filtered_messages.append(i)
    
    return jsonify({'status': 'ok', 'messages': filtered_messages})
if __name__ == '__main__':
    socketio.run(app, debug=True)

