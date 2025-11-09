import os
import json
import uuid
import random
from datetime import datetime, date
from flask import Flask, request, session, redirect, url_for
import pandas as pd

app = Flask(__name__)
app.secret_key = "replace_this_secret_in_production_2025"

STATE_FILE = "wellness_state.json"

# --- Static Data (as per report) ---
COUNSELORS = [
    {"name": "Dr. Priya Sharma", "specialty": "Stress & Anxiety"},
    {"name": "Ms. Neha Verma", "specialty": "Grief & Loss"},
    {"name": "Mr. Rohan Gupta", "specialty": "Relationship Issues"},
]

# Added links to each resource
RESOURCES = [
    {
        'ID': 'R001',
        'Title': 'Quick Grounding Exercise',
        'Type': 'Text',
        'Category': 'Anxiety',
        'Description': 'A simple technique to focus on the present moment.',
        'Link': 'https://www.healthline.com/health/grounding-techniques'
    },
    {
        'ID': 'R002',
        'Title': 'Gentle Guided Meditation',
        'Type': 'Audio',
        'Category': 'Mindfulness',
        'Description': 'A 10-minute audio to help relax your mind and body.',
        'Link': 'https://www.youtube.com/watch?v=inpok4MKVLM'
    },
    {
        'ID': 'R003',
        'Title': 'Understanding Stress Cycles',
        'Type': 'Video',
        'Category': 'Wellness',
        'Description': 'An informational video explaining how stress affects the body.',
        'Link': 'https://www.youtube.com/watch?v=hnpQrMqDoqE'
    },
    {
        'ID': 'R004',
        'Title': 'Helpful Helpline Numbers',
        'Type': 'Text',
        'Category': 'Crisis',
        'Description': 'A list of 24/7 crisis and support phone numbers.',
        'Link': 'https://findahelpline.com'
    },
    {
        'ID': 'R005',
        'Title': 'Managing Anxiety with Breathing',
        'Type': 'Text',
        'Category': 'Anxiety',
        'Description': 'A step-by-step guide to 4-7-8 breathing.',
        'Link': 'https://psychcentral.com/health/4-7-8-breathing'
    }
]

# -------------------------
# JSON State Management
# -------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {
        "peer_queue": [],
        "booked_requests": [],
        "active_rooms": {},
        "rooms": {},
        "chat_logs": []
    }

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# -------------------------
# Backend Logic
# -------------------------
class WellnessSystem:
    def __init__(self):
        self.state = load_state()
        self.peer_queue = self.state.get('peer_queue', [])
        self.booked_requests = self.state.get('booked_requests', [])
        self.active_rooms = self.state.get('active_rooms', {})
        self.rooms = self.state.get('rooms', {})
        self.chat_logs = self.state.get('chat_logs', [])

    def simulate_bot_response(self, message, last_intent=None):
        m = (message or "").lower().strip()
        crisis_keywords = ["suicide", "end my life", "kill myself", "self harm", "i can't go on", "i cant go on", "die"]
        if any(k in m for k in crisis_keywords):
            return {"response": "🚨 *IMMEDIATE DANGER DETECTED!* 🚨 Please reach out now: <a href='https://findahelpline.com' target='_blank'>Find Helpline</a>", "intent": "crisis_alert", "actions": []}

        sadness_keys = ["depressed", "depression", "sad", "unhappy", "low", "down", "hopeless"]
        anxiety_keys = ["stressed", "stress", "anxiety", "anxious", "worried", "panic"]
        lonely_keys = ["alone", "lonely"]

        if any(k in m for k in sadness_keys + anxiety_keys + lonely_keys):
            resp = random.choice([
                "I'm really sorry you're feeling that way 💚 You’re not alone.",
                "That sounds really tough. Let's find something that can help.",
                "I hear you. Let's explore some support options below."
            ])
            actions = [
                ("💬 Talk to a peer", "/peer"),
                ("👩‍⚕️ Request a counselor", "/book"),
                ("🧘 View calming resources", "/resources")
            ]
            return {"response": resp, "intent": "serious_emotion", "actions": actions}

        if any(g in m for g in ["hi", "hello", "hey"]):
            return {"response": "Hello! I'm your wellness assistant 🌱 How are you feeling today?", "intent": "greeting", "actions": []}

        return {"response": "I'm here for you. Would you like to explore resources or connect with a peer?", 
                "intent": "unknown", 
                "actions": [("💬 Talk to a peer", "/peer"),("👩‍⚕️ Request a counselor", "/book"),("🧘 View resources", "/resources")]}

    def add_booking(self, counselor_name, date_str, time_str, user_id=None):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None, "Invalid date format."
        if d < date.today():
            return None, "Date is in the past."
        req = {"id": str(uuid.uuid4())[:10], "counselor": counselor_name, "date": date_str, "time": time_str, "status": "Pending Confirmation", "user_id": user_id}
        self.booked_requests.append(req)
        self.state['booked_requests'] = self.booked_requests
        save_state(self.state)
        return req, None

    # Peer-to-peer functions
    def join_queue_and_match(self, user_id, topic=None):
        state = load_state()
        queue = state.get("peer_queue", [])
        partner = None
        for i, uid in enumerate(queue):
            if uid != user_id:
                partner = uid
                queue.pop(i)
                break
        if partner:
            room_id = str(uuid.uuid4())[:8]
            ar = state.get("active_rooms", {})
            ar[user_id] = {"room_id": room_id, "partner_id": partner, "topic": topic}
            ar[partner] = {"room_id": room_id, "partner_id": user_id, "topic": topic}
            rooms = state.get("rooms", {})
            rooms[room_id] = []
            state.update({"peer_queue": queue, "active_rooms": ar, "rooms": rooms})
            save_state(state)
            return {"matched": True, "room_id": room_id, "partner_id": partner}
        if user_id not in queue:
            queue.append(user_id)
        state["peer_queue"] = queue
        save_state(state)
        return {"matched": False, "queue_size": len(queue)}

    def post_room_message(self, room_id, who_label, text):
        state = load_state()
        rooms = state.get("rooms", {})
        if room_id not in rooms:
            rooms[room_id] = []
        ts = datetime.utcnow().isoformat()
        rooms[room_id].append({"who": who_label, "text": text, "ts": ts})
        state["rooms"] = rooms
        save_state(state)

    def get_active_room_for_user(self, user_id):
        return load_state().get("active_rooms", {}).get(user_id)

    def end_room(self, room_id):
        state = load_state()
        ar = state.get("active_rooms", {})
        for uid, info in list(ar.items()):
            if info.get("room_id") == room_id:
                ar.pop(uid)
        state["active_rooms"] = ar
        save_state(state)

system = WellnessSystem()

# -------------------------
# UI & Routes
# -------------------------
def get_session_user_id():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())[:8]
    return session['user_id']

BASE_NAV = """
<div style="background:#007f5f;padding:12px;">
  <a href="/" style="color:white;margin-right:20px;">🏠 Home</a>
  <a href="/chat" style="color:white;margin-right:20px;">💬 Chat</a>
  <a href="/peer" style="color:white;margin-right:20px;">🤝 Peer Chat</a>
  <a href="/book" style="color:white;margin-right:20px;">📅 Book</a>
  <a href="/resources" style="color:white;">📚 Resources</a>
</div>
"""

@app.route("/")
def home():
    uid = get_session_user_id()
    return BASE_NAV + f"""
    <div style='font-family:Arial;margin:30px;'>
    <h1>🌿 Digital Wellness Support System</h1>
    <p>Welcome! Your anonymous ID: <b>{uid}</b></p>
    <p>Use the Chatbot for emotional support, connect with peers, or request a counselor.</p>
    </div>
    """

@app.route("/chat", methods=["GET","POST"])
def chat():
    uid = get_session_user_id()
    if 'chat_history' not in session:
        session['chat_history'] = [{'type':'bot','text':"Hi — I'm your first-level wellness assistant. How can I support you today?"}]
        session['last_intent'] = None

    history = session['chat_history']
    last_intent = session.get('last_intent')

    if request.method == "POST":
        user_msg = request.form.get("message","").strip()
        if user_msg:
            history.append({'type':'user','text': user_msg})
            bot_data = system.simulate_bot_response(user_msg, last_intent)
            bot_resp = bot_data.get('response','')
            intent = bot_data.get('intent','unknown')
            actions = bot_data.get('actions', [])
            history.append({'type':'bot','text': bot_resp})
            if actions:
                buttons_html = "".join([f"<a href='{path}' style='display:inline-block;margin:6px;padding:8px 12px;background:#007f5f;color:white;border-radius:6px;text-decoration:none;'>{label}</a>" for label, path in actions])
                history.append({'type':'bot','text': buttons_html})
            session['chat_history'] = history
            session['last_intent'] = intent
        return redirect(url_for('chat'))

    chat_html = ""
    for msg in history:
        align = 'right' if msg['type']=='user' else 'left'
        color = '#000' if msg['type']=='user' else '#006400'
        chat_html += f"<div style='text-align:{align};margin:6px;color:{color}'><b>{'You' if msg['type']=='user' else 'Bot'}:</b> {msg['text']}</div>"

    return BASE_NAV + f"""
    <div style='font-family:Arial;width:80%;margin:20px auto;'>
      <h2>💬 Chatbot</h2>
      <div style='border:1px solid #ccc;padding:10px;height:320px;overflow:auto;background:#f9f9f9;'>{chat_html}</div>
      <form method='POST' style='margin-top:10px;'>
        <input name='message' placeholder='Type here...' style='width:70%;padding:8px;' required>
        <button type='submit' style='padding:8px;background:#007f5f;color:white;border:none;border-radius:6px;'>Send</button>
        <a href='/chat/clear' style='margin-left:10px;'>Clear</a>
      </form>
    </div>
    """

@app.route("/chat/clear")
def chat_clear():
    session.pop('chat_history', None)
    session.pop('last_intent', None)
    return redirect(url_for('chat'))

@app.route("/peer", methods=["GET","POST"])
def peer():
    uid = get_session_user_id()
    msg = ""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "join":
            topic = request.form.get("topic") or None
            res = system.join_queue_and_match(uid, topic)
            if res.get("matched"):
                return redirect(url_for("room", room_id=res["room_id"]))
            else:
                msg = f"You joined the queue. Queue size: {res.get('queue_size')}"
        elif action == "leave":
            system.leave_queue(uid)
            msg = "Left the queue."

    st = load_state()
    qlen = len(st.get("peer_queue", []))
    active = system.get_active_room_for_user(uid)
    active_html = f"<p>You are in room <b>{active['room_id']}</b>. <a href='/room/{active['room_id']}'>Open</a></p>" if active else ""

    return BASE_NAV + f"""
    <div style='font-family:Arial;margin:30px;width:60%;'>
      <h2>🤝 Peer Chat</h2>
      <p>{msg}</p>{active_html}
      <form method='POST'>
        <label>Topic (optional)</label><br>
        <input name='topic' placeholder='e.g. stress, anxiety' style='width:100%;padding:8px;'><br><br>
        <button name='action' value='join' style='padding:8px 12px;background:#007f5f;color:white;border:none;border-radius:6px;'>Join Queue</button>
        <button name='action' value='leave' style='padding:8px 12px;margin-left:8px;'>Leave Queue</button>
      </form>
      <hr><p>Queue length: {qlen}</p>
    </div>
    """

@app.route("/room/<room_id>", methods=["GET","POST"])
def room(room_id):
    uid = get_session_user_id()
    st = load_state()
    messages = st.get("rooms", {}).get(room_id, [])
    if request.method == "POST":
        text = request.form.get("text","").strip()
        if text:
            system.post_room_message(room_id, uid, text)
            return redirect(url_for("room", room_id=room_id))
    html = "".join([f"<div style='margin:6px;'><b>{m['who']}</b>: {m['text']}</div>" for m in messages])
    return BASE_NAV + f"""
    <div style='font-family:Arial;width:80%;margin:20px auto;'>
      <h2>Room {room_id}</h2>
      <div style='border:1px solid #ccc;padding:10px;height:300px;overflow:auto;background:white;'>{html or '<i>No messages yet</i>'}</div>
      <form method='POST' style='margin-top:8px;'>
        <input name='text' placeholder='Type message...' style='width:70%;padding:8px;' required>
        <button type='submit' style='padding:8px;background:#007f5f;color:white;border:none;border-radius:6px;'>Send</button>
      </form>
    </div>
    """

@app.route("/book", methods=["GET","POST"])
def book():
    uid = get_session_user_id()
    if request.method == "POST":
        counselor = request.form.get("counselor")
        date_str = request.form.get("date")
        time_str = request.form.get("time")
        req, err = system.add_booking(counselor, date_str, time_str, uid)
        if err:
            return BASE_NAV + f"<div style='margin:30px;font-family:Arial;color:red;'>Error: {err}</div>"
        return BASE_NAV + f"<div style='margin:30px;font-family:Arial;'><h3>✅ Booking Confirmed</h3><p>{counselor} on {date_str} at {time_str}</p></div>"

    options = "".join([f"<option value='{c['name']}'>{c['name']} ({c['specialty']})</option>" for c in COUNSELORS])
    return BASE_NAV + f"""
    <div style='font-family:Arial;margin:30px;width:60%;'>
      <h2>📅 Book Counseling</h2>
      <form method='POST'>
        <label>Counselor</label><br>
        <select name='counselor' required style='width:100%;padding:8px;'>{options}</select><br><br>
        <label>Date</label><br>
        <input name='date' type='date' required style='width:100%;padding:8px;'><br><br>
        <label>Time</label><br>
        <input name='time' required style='width:100%;padding:8px;'><br><br>
        <button type='submit' style='padding:8px 12px;background:#007f5f;color:white;border:none;border-radius:6px;'>Submit</button>
      </form>
    </div>
    """

@app.route("/resources")
def resources():
    html = ""
    for r in RESOURCES:
        html += f"""
        <div style='border:1px solid #ccc;padding:12px;margin:8px;border-radius:8px;background:#f9f9f9;'>
            <h3>{r['Title']} <small style='color:#666;'>({r['Type']} | {r['Category']})</small></h3>
            <p>{r['Description']}</p>
            <a href='{r['Link']}' target='_blank' style='background:#007f5f;color:white;padding:6px 10px;border-radius:5px;text-decoration:none;'>🔗 Open Resource</a>
        </div>
        """
    return BASE_NAV + f"<div style='font-family:Arial;margin:20px;'><h2>📚 Resources</h2>{html}</div>"

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    st = load_state()
    save_state(st)
    os.makedirs("static", exist_ok=True)
    print("✅ Running Digital Wellness System on http://127.0.0.1:5000/")
    app.run(debug=True)
