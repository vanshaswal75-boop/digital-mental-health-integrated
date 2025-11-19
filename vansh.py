import os
import json
import uuid
import random
from datetime import datetime

from flask import Flask, request, session, redirect, url_for, jsonify
from markupsafe import escape
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.secret_key = "wellness_app_secret_2025"

socketio = SocketIO(app, async_mode="eventlet")

STATE_FILE = "wellness_state.json"
CHAT_LOG_CSV = "chat_logs.csv"

waiting_user = None
user_rooms = {}


# -------------------- UTILITIES --------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                if "bookings" not in state:
                    state["bookings"] = []
                return state
        except:
            pass
    return {"bookings": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def ensure_chat_log():
    if not os.path.exists(CHAT_LOG_CSV):
        with open(CHAT_LOG_CSV, "w", encoding="utf-8") as f:
            f.write("anon_id,timestamp,sender,message\n")

def log_chat(anon_id, sender, message):
    ensure_chat_log()
    ts = datetime.utcnow().isoformat()
    safe = message.replace("\n", " ").replace(",", " ")
    with open(CHAT_LOG_CSV, "a", encoding="utf-8") as f:
        f.write(f"{anon_id},{ts},{sender},{safe}\n")

def get_anon():
    if "anon_id" not in session:
        session["anon_id"] = "a-" + uuid.uuid4().hex[:8]
    return session["anon_id"]


# -------------------- UPGRADED SMART CHATBOT --------------------
def bot_reply(text):
    t = (text or "").lower().strip()

    crisis = [
        "suicide", "kill myself", "die", "end my life",
        "want to die", "give up", "self harm", "cut myself"
    ]

    medium = [
        "stress", "anxiety", "sad", "panic", "overwhelmed",
        "tired", "depressed", "worthless", "lonely"
    ]

    peer_keywords = ["peer chat", "peer", "talk to someone"]
    res_keywords = ["resource", "resources", "material", "help article"]
    book_keywords = ["book", "session", "appointment", "counselor", "counselling"]

    greetings = ["hi", "hello", "hey", "wassup", "sup", "yo", "hiii"]

    # Human-like greetings
    greeting_responses = [
        "Hey! It’s nice to hear from you. How are you feeling today?",
        "Hello! I'm here with you — what’s on your mind?",
        "Hi! Tell me whatever you feel comfortable sharing.",
        "Hey! I'm listening. How are things going?"
    ]

    # Empathetic supporting replies
    natural_replies = [
        "I understand… that must be tough. What made you feel this way?",
        "Thanks for sharing that. Want to talk about what started these feelings?",
        "I hear you. It’s okay to feel this way. What happened?",
        "That sounds heavy… I’m here with you. Want to explain more?",
        "Emotions can feel overwhelming sometimes. Want to share more?",
        "I'm here for you. Take your time — what’s bothering you?"
    ]

    # Crisis detection
    if any(w in t for w in crisis):
        return {
            "type": "crisis",
            "message": (
                "⚠ I’m really worried for your safety.<br>"
                "Please reach out immediately.<br><br>"
                "📞 <b>AASRA:</b> 91-9820466726<br>"
                "📞 <b>Snehi:</b> +91-9582208181<br>"
            )
        }

    # Redirect triggers
    if any(w in t for w in peer_keywords):
        return {"type": "redirect_peer", "message": "Connecting you to a peer…"}

    if any(w in t for w in res_keywords):
        return {"type": "redirect_resources", "message": "Taking you to resources…"}

    if any(w in t for w in book_keywords):
        return {"type": "redirect_book", "message": "Opening counseling session booking…"}

    # Medium distress → show soft option cards
    if any(w in t for w in medium):
        return {
            "type": "choices",
            "message": (
                "<div style='margin:10px 0;font-size:15px;color:#333;'>"
                "It sounds like you're going through something difficult. I’m here with you — "
                "you can choose what feels right for you:"
                "</div>"

                "<div style='background:#e8f9f0;padding:12px;margin:8px 0;border-radius:10px;"
                "box-shadow:0 2px 6px rgba(0,0,0,0.1);'>"
                "<a href='/peer' style='text-decoration:none;color:#2b6e4f;font-weight:600;'>💬 Peer Chat</a></div>"

                "<div style='background:#eef2ff;padding:12px;margin:8px 0;border-radius:10px;"
                "box-shadow:0 2px 6px rgba(0,0,0,0.1);'>"
                "<a href='/resources' style='text-decoration:none;color:#3b4fa4;font-weight:600;'>📚 Wellness Resources</a></div>"

                "<div style='background:#fff3df;padding:12px;margin:8px 0;border-radius:10px;"
                "box-shadow:0 2px 6px rgba(0,0,0,0.1);'>"
                "<a href='/book' style='text-decoration:none;color:#aa5a00;font-weight:600;'>🧑‍⚕ Book a Counseling Session</a></div>"
            )
        }

    # Greetings
    if any(t.startswith(g) for g in greetings):
        return {"type": "normal", "message": random.choice(greeting_responses)}

    # Normal supportive conversation
    return {"type": "normal", "message": random.choice(natural_replies)}


# -------------------- NEW HOMEPAGE WITH 4 OPTIONS --------------------
@app.route("/")
def home():
    anon = get_anon()
    return f"""
    <html><head>
    <style>
    body {{
        font-family: Arial;
        background: linear-gradient(to bottom, #dff6ff, #ffffff);
        padding: 40px;
    }}
    .menu {{
        max-width: 700px;
        margin: auto;
        background: white;
        padding: 30px;
        border-radius: 14px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
    }}
    .btn {{
        display:block;
        padding:12px;
        margin:10px auto;
        width:80%;
        background:#2b6e4f;
        color:white;
        text-decoration:none;
        border-radius:8px;
        font-size:15px;
        font-weight:600;
    }}
    </style>
    </head>
    <body>

    <div class="menu">
        <h2 style="color:#2b6e4f;">Digital Wellness Assistant</h2>
        <p>Your anonymous ID: <b>{escape(anon)}</b></p>

        <a href="/chat" class="btn">🤖 Chat with Wellness Bot</a>
        <a href="/peer" class="btn" style="background:#3d8f68;">💬 Peer-to-Peer Chat</a>
        <a href="/resources" class="btn" style="background:#597dff;">📚 Wellness Resources</a>
        <a href="/book" class="btn" style="background:#ff9f45;">🧑‍⚕ Book a Counseling Session</a>
    </div>

    </body></html>
    """


# -------------------- CHATBOT PAGE --------------------
@app.route("/chat")
def chat():
    anon = get_anon()
    return f"""
    <html><head>
    <style>
    body {{ font-family:Arial; background:#f3f9fb; padding:20px; }}
    .chatbox {{
        background:white; border-radius:10px; padding:20px;
        max-width:700px; margin:auto;
        box-shadow:0 4px 14px rgba(0,0,0,0.1);
    }}
    #messages {{
        height:350px; overflow:auto; padding:10px;
        border:1px solid #ddd; border-radius:8px;
        background:#fafafa;
    }}
    .input-area {{
        margin-top:10px; display:flex; gap:8px;
    }}
    input {{
        flex:1; padding:10px; border-radius:8px; border:1px solid #ccc;
    }}
    button {{
        background:#2b6e4f; color:white; border:none; border-radius:8px;
        padding:10px 16px;
    }}
    </style>
    </head>
    <body>

    <div class="chatbox">
      <h3 style="color:#2b6e4f;">Chat with Wellness Assistant</h3>

      <div id="messages"></div>

      <div class="input-area">
        <input id="text" placeholder="Type your message...">
        <button onclick="sendMsg()">Send</button>
      </div>
    </div>

<script>
function append(who, msg) {{
    let m = document.getElementById("messages");
    let div = document.createElement("div");
    div.style.margin = "8px 0";
    div.innerHTML = "<b>" + who + ":</b> " + msg;
    m.appendChild(div);
    m.scrollTop = m.scrollHeight;
}}

async function sendMsg() {{
    let inp = document.getElementById("text");
    let t = inp.value.trim();
    if (!t) return;
    append("You", t);
    inp.value = "";

    let r = await fetch("/chatbot", {{
        method:"POST",
        headers:{{"Content-Type":"application/json"}},
        body:JSON.stringify({{anon_id:"{anon}", message:t}})
    }});
    let data = await r.json();
    append("Bot", data.message);

    if (data.type === "redirect_peer") {{
        window.location.href = "/peer";
    }}
    if (data.type === "redirect_resources") {{
        window.location.href = "/resources";
    }}
    if (data.type === "redirect_book") {{
        window.location.href = "/book";
    }}
}}
</script>

    </body></html>
    """


# -------------------- HELP PAGE --------------------
@app.route("/help")
def help_page():
    anon = get_anon()
    return f"""
    <div style="font-family:Arial;max-width:650px;margin:40px auto;background:white;padding:20px;
                border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,0.1);">

      <h3 style="color:#2b6e4f;">Support Options</h3>
      <p>Your ID: <b>{escape(anon)}</b></p>

      <a href="/peer" style="display:block;padding:10px;background:#2b6e4f;color:white;
                             text-decoration:none;margin:8px;border-radius:6px;">💬 Peer Chat</a>

      <a href="/resources" style="display:block;padding:10px;background:#597dff;color:white;
                                 text-decoration:none;margin:8px;border-radius:6px;">📚 Resources</a>

      <a href="/book" style="display:block;padding:10px;background:#ff9f45;color:white;
                             text-decoration:none;margin:8px;border-radius:6px;">🧑‍⚕ Book Session</a>

      <a href="/" style="color:#2b6e4f;">← Back</a>
    </div>
    """


# -------------------- PEER CHAT PAGE --------------------
@app.route("/peer")
def peer():
    anon = get_anon()
    return f"""
    <html><head>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
    body {{ font-family:Arial;background:#f3f9fb;padding:20px; }}
    .box {{
        background:white;max-width:700px;margin:auto;padding:20px;border-radius:12px;
        box-shadow:0 4px 14px rgba(0,0,0,0.1);
    }}
    #chatbox {{
        height:330px;border:1px solid #ccc;border-radius:8px;padding:10px;
        overflow:auto;background:#fafafa;
    }}
    </style>
    </head>

    <body>
      <div class="box">
        <h3 style="color:#2b6e4f;">Peer Support Chat</h3>
        <p>Your ID: <b>{escape(anon)}</b></p>

        <div id="status" style="margin-bottom:10px;">Connecting...</div>
        <div id="chatbox"></div>

        <form id="form" style="display:flex;gap:8px;margin-top:10px;">
          <input id="msg" placeholder="Type a message..."
                 style="flex:1;padding:10px;border:1px solid #ccc;border-radius:8px;">
          <button style="background:#2b6e4f;color:white;border:none;border-radius:8px;padding:10px 18px;">Send</button>
        </form>
      </div>

<script>
const anon = "{escape(anon)}";
const socket = io();

function append(who, text) {{
    const box = document.getElementById("chatbox");
    let div = document.createElement("div");
    div.style.margin = "6px 0";
    div.innerHTML = "<b>" + who + ":</b> " + text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}}

socket.on("connect", () => {{
    document.getElementById("status").innerText = "Connected. Waiting for peer...";
    socket.emit("join_peer", {{anon_id: anon}});
}});

socket.on("status", data => {{
    document.getElementById("status").innerText = data.message;
}});

socket.on("peer_message", data => {{
    append(data.from, data.message);
}});

document.getElementById("form").addEventListener("submit", function(e){{
    e.preventDefault();
    let text = document.getElementById("msg").value.trim();
    if (!text) return;
    append("You", text);
    socket.emit("peer_message", {{anon_id: anon, message: text}});
    document.getElementById("msg").value = "";
}});
</script>

    </body></html>
    """


# -------------------- OTHER ROUTES --------------------
@app.route("/resources")
def resources():
    return """
    <div style="font-family:Arial;max-width:650px;margin:40px auto;background:white;padding:20px;
                border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,0.1);">
      <h3 style="color:#2b6e4f;">Helpful Resources</h3>
      <ul>
        <li><a target="_blank" href="https://www.healthline.com/health/grounding-techniques">Grounding Techniques</a></li>
        <li><a target="_blank" href="https://www.youtube.com/watch?v=inpok4MKVLM">Breathing Exercise</a></li>
        <li><a target="_blank" href="https://www.youtube.com/watch?v=hnpQrMqDoqE">Stress Explained</a></li>
      </ul>
      <a href="/help" style="color:#2b6e4f;">← Back</a>
    </div>
    """


@app.route("/book", methods=["GET", "POST"])
def book():
    anon = get_anon()
    state = load_state()

    if request.method == "POST":
        dt = request.form.get("datetime", "").strip()
        if dt:
            state["bookings"].append({"anon_id": anon, "datetime": dt})
            save_state(state)
            return f"<p>Session booked for {escape(dt)} ✔</p><a href='/help'>Back</a>"

    return """
    <div style="font-family:Arial;max-width:650px;margin:40px auto;background:white;padding:20px;
                border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,0.1);">
      <h3 style="color:#2b6e4f;">Book a Session</h3>
      <form method="POST">
        <input name="datetime" placeholder="YYYY-MM-DD HH:MM"
               style="padding:10px;border-radius:8px;border:1px solid #ccc;">
        <button style="padding:10px;background:#2b6e4f;color:white;border:none;border-radius:8px;">Book</button>
      </form>
      <a href="/help" style="color:#2b6e4f;">← Back</a>
    </div>
    """


# -------------------- CHATBOT API --------------------
@app.route("/chatbot", methods=["POST"])
def chatbot_api():
    data = request.get_json() or {}
    msg = (data.get("message") or "").strip()
    anon = data.get("anon_id") or get_anon()

    bot = bot_reply(msg)

    if msg:
        log_chat(anon, "user", msg)
    log_chat(anon, "bot", bot["message"])

    return jsonify(bot)


# -------------------- SOCKET EVENTS FOR PEER CHAT --------------------
@socketio.on("join_peer")
def join_peer(data):
    global waiting_user
    sid = request.sid
    anon = data.get("anon_id")

    if waiting_user is None:
        waiting_user = {"sid": sid, "anon": anon}
        emit("status", {"message": "Waiting for peer..."})
    else:
        room = "room-" + uuid.uuid4().hex[:6]

        join_room(room, sid=sid)
        join_room(room, sid=waiting_user["sid"])

        user_rooms[sid] = room
        user_rooms[waiting_user["sid"]] = room

        emit("status", {"message": "Connected! Start chatting."}, room=room)
        waiting_user = None


@socketio.on("peer_message")
def peer_message(data):
    sid = request.sid
    room = user_rooms.get(sid)
    if room:
        emit("peer_message", {"from": data["anon_id"], "message": data["message"]}, room=room)


@socketio.on("disconnect")
def disconnect():
    global waiting_user
    sid = request.sid

    if waiting_user and waiting_user["sid"] == sid:
        waiting_user = None

    room = user_rooms.pop(sid, None)
    if room:
        emit("status", {"message": "Your peer disconnected."}, room=room)


# -------------------- RUN --------------------
if __name__ == "__main__":
    ensure_chat_log()
    print("Server running → http://127.0.0.1:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

