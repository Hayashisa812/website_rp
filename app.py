from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import time

app = Flask(__name__)
socketio = SocketIO(app)

# 掲示板ごとのメッセージ保存
message_store = {}
member_store = {}

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
    
    msg = {
        'reaction': data['reaction'],
        'id': data['id'],

    }
    socketio.emit('reaction', msg)
    return jsonify({'status': 'ok'})
@app.route('/member/<board_name>', methods=['POST'])


def get_member(board_name):
    data = request.json
    #print(data['sender'])
    member_store.setdefault(board_name, []).append(data['sender'])
    member_store[board_name] = list(set(member_store[board_name]))
    print(member_store," member_store")
    
                
    socketio.emit('member', member_store)

    return jsonify({'status': 'ok'})
@app.route('/del_member/<board_name>', methods=['POST'])
def del_member(board_name):
    data = request.json
    print(data['sender'])
    if board_name in member_store:
        member_store[board_name] = [m for m in member_store[board_name] if m != data['sender']]
        socketio.emit('member', member_store)
    return jsonify({'status': 'ok'})
if __name__ == '__main__':
    socketio.run(app, debug=True)

