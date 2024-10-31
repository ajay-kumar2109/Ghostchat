from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Store active users and pairs
waiting_users = []
pairs = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'id': request.sid})

@socketio.on('search')
def handle_search():
    user_sid = request.sid
    print(f'Search request from: {user_sid}')
    
    # Remove user from any existing pair
    for pair in pairs.items():
        if user_sid in pair:
            del pairs[pair[0]]
    
    # If user was waiting, remove them
    if user_sid in waiting_users:
        waiting_users.remove(user_sid)
    
    # If someone is waiting, make a pair
    if waiting_users:
        partner_sid = waiting_users.pop(0)
        pairs[user_sid] = partner_sid
        pairs[partner_sid] = user_sid
        # Notify both users
        emit('matched', to=user_sid)
        emit('matched', to=partner_sid)
        print(f'Matched {user_sid} with {partner_sid}')
    else:
        # Add user to waiting list
        waiting_users.append(user_sid)
        emit('waiting', to=user_sid)
        print(f'Added {user_sid} to waiting list')

@socketio.on('message')
def handle_message(data):
    user_sid = request.sid
    if user_sid in pairs:
        partner_sid = pairs[user_sid]
        emit('message', data, to=partner_sid)

@socketio.on('disconnect')
def handle_disconnect():
    user_sid = request.sid
    print(f'Client disconnected: {user_sid}')
    
    # Remove from waiting list if present
    if user_sid in waiting_users:
        waiting_users.remove(user_sid)
    
    # Handle partner notification if paired
    if user_sid in pairs:
        partner_sid = pairs[user_sid]
        # Remove both users from pairs
        del pairs[user_sid]
        if partner_sid in pairs:
            del pairs[partner_sid]
        # Notify partner
        emit('partner_left', to=partner_sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
