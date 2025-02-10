from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS
from pymongo import MongoClient
import eventlet

# Initialize Flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ✅ Connect to MongoDB
MONGO_URI = "mongodb+srv://ahammedmass24:<db_password>@cluster0.zow04.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['smart_classroom']
meetings_collection = db['meetings']

# Store active rooms
active_rooms = {}

# ✅ Create a Meeting (Teacher)
@app.route('/create_meeting', methods=['POST'])
def create_meeting():
    data = request.json
    meeting_id = data.get("meeting_id")

    if not meeting_id:
        return jsonify({"error": "Meeting ID required"}), 400

    # Check if meeting already exists
    if meetings_collection.find_one({"meeting_id": meeting_id}):
        return jsonify({"message": "Meeting already exists"}), 200

    # Store meeting in MongoDB
    meetings_collection.insert_one({"meeting_id": meeting_id, "users": []})

    return jsonify({"message": "Meeting created successfully", "meeting_id": meeting_id}), 201


# ✅ Join Meeting (Student)
@app.route('/join_meeting', methods=['POST'])
def join_meeting():
    data = request.json
    meeting_id = data.get("meeting_id")

    # Check if meeting exists
    meeting = meetings_collection.find_one({"meeting_id": meeting_id})
    if not meeting:
        return jsonify({"error": "Meeting not found"}), 404

    return jsonify({"message": "Joined meeting successfully", "meeting_id": meeting_id})


# ✅ Handle WebRTC Offer (Teacher -> Student)
@socketio.on("offer")
def handle_offer(data):
    room = data.get("room")
    offer = data.get("offer")

    if room in active_rooms:
        emit("offer", {"offer": offer}, room=room)


# ✅ Handle WebRTC Answer (Student -> Teacher)
@socketio.on("answer")
def handle_answer(data):
    room = data.get("room")
    answer = data.get("answer")

    if room in active_rooms:
        emit("answer", {"answer": answer}, room=room)


# ✅ Handle ICE Candidates (WebRTC peer connection)
@socketio.on("ice-candidate")
def handle_ice_candidate(data):
    room = data.get("room")
    candidate = data.get("candidate")

    if room in active_rooms:
        emit("ice-candidate", {"candidate": candidate}, room=room)


# ✅ Handle Room Join (WebRTC Room)
@socketio.on("join-room")
def handle_join_room(data):
    room = data.get("room")
    join_room(room)

    if room not in active_rooms:
        active_rooms[room] = []
    active_rooms[room].append(request.sid)

    emit("room-joined", {"room": room}, room=room)


# ✅ Handle Room Leave
@socketio.on("leave-room")
def handle_leave_room(data):
    room = data.get("room")
    leave_room(room)

    if room in active_rooms and request.sid in active_rooms[room]:
        active_rooms[room].remove(request.sid)

    emit("room-left", {"room": room}, room=room)


# ✅ Run Flask App
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
