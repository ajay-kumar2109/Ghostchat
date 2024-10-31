from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users
waiting_users = []
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = request.sid
    print(f'Client connected: {user_id}')
    active_users[user_id] = {'partner': None}
    emit('connected', {'status': 'Connected to server'})

@socketio.on('search')
def handle_search():
    user_id = request.sid
    print(f'Search request from: {user_id}')

    # If user was already waiting, remove them
    if user_id in waiting_users:
        waiting_users.remove(user_id)

    # If user had a partner, disconnect them
    if active_users[user_id]['partner']:
        partner_id = active_users[user_id]['partner']
        active_users[user_id]['partner'] = None
        if partner_id in active_users:
            active_users[partner_id]['partner'] = None
            emit('partner_left', room=partner_id)

    # If someone is waiting, match them
    if waiting_users:
        partner_id = waiting_users.pop(0)
        if partner_id in active_users:  # Make sure partner still exists
            # Match the users
            active_users[user_id]['partner'] = partner_id
            active_users[partner_id]['partner'] = user_id
            # Notify both users
            emit('matched', {'partnerId': partner_id}, room=user_id)
            emit('matched', {'partnerId': user_id}, room=partner_id)
            print(f'Matched {user_id} with {partner_id}')
    else:
        # Add user to waiting list
        waiting_users.append(user_id)
        emit('waiting', {'status': 'Waiting for partner'}, room=user_id)
        print(f'Added {user_id} to waiting list')

@socketio.on('message')
def handle_message(data):
    user_id = request.sid
    if user_id in active_users and active_users[user_id]['partner']:
        partner_id = active_users[user_id]['partner']
        emit('message', data, room=partner_id)

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    print(f'Client disconnected: {user_id}')
    
    # Remove from waiting list
    if user_id in waiting_users:
        waiting_users.remove(user_id)
    
    # Notify partner if exists
    if user_id in active_users and active_users[user_id]['partner']:
        partner_id = active_users[user_id]['partner']
        if partner_id in active_users:
            active_users[partner_id]['partner'] = None
            emit('partner_left', room=partner_id)
    
    # Remove user from active users
    if user_id in active_users:
        del active_users[user_id]

if __name__ == '__main__':
    socketio.run(app, debug=True)
