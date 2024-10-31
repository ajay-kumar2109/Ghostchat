from flask import Flask, render_template, request
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

@socketio.on('search')
def handle_search():
    user_sid = request.sid
    print(f'Search request from user: {user_sid}')
    
    # If user is already paired, unpair them
    if user_sid in pairs:
        old_partner = pairs[user_sid]
        del pairs[user_sid]
        del pairs[old_partner]
        emit('partner_left', to=old_partner)
        print(f'Unpaired existing match: {user_sid} and {old_partner}')
    
    # Remove user from waiting list if they're there
    if user_sid in waiting_users:
        waiting_users.remove(user_sid)
    
    # Look for a partner
    if waiting_users:
        partner_sid = waiting_users.pop(0)
        if partner_sid != user_sid and partner_sid not in pairs:
            # Create new pair
            pairs[user_sid] = partner_sid
            pairs[partner_sid] = user_sid
            
            print(f'Matched users: {user_sid} with {partner_sid}')
            print(f'Current pairs: {pairs}')
            
            # Notify both users
            emit('matched', to=user_sid)
            emit('matched', to=partner_sid)
            return
    
    # No partner found, add to waiting list
    waiting_users.append(user_sid)
    emit('waiting', to=user_sid)
    print(f'User {user_sid} added to waiting list. Current waiting: {waiting_users}')

@socketio.on('message')
def handle_message(data):
    user_sid = request.sid
    if user_sid in pairs:
        partner_sid = pairs[user_sid]
        emit('message', {
            'name': data['name'],
            'message': data['message']
        }, to=partner_sid)
        print(f'Message sent from {user_sid} to {partner_sid}')

@socketio.on('disconnect')
def handle_disconnect():
    user_sid = request.sid
    print(f'Client disconnected: {user_sid}')
    
    # Remove from waiting list if present
    if user_sid in waiting_users:
        waiting_users.remove(user_sid)
        print(f'Removed {user_sid} from waiting list')
    
    # Handle partner notification if paired
    if user_sid in pairs:
        partner_sid = pairs[user_sid]
        # Remove both users from pairs
        del pairs[user_sid]
        if partner_sid in pairs:
            del pairs[partner_sid]
        # Notify partner
        emit('partner_left', to=partner_sid)
        print(f'Notified partner {partner_sid} of disconnect')

if __name__ == '__main__':
    socketio.run(app, debug=True)
