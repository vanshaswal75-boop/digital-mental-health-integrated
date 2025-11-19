import os
import json
import uuid
import random
from datetime import datetime
from flask import Flask, request, session, redirect, url_for, jsonify
from markupsafe import escape


app = Flask(_name_)
app.secret_key = "replace_this_secret_in_production_2025"

STATE_FILE = "wellness_state.json"
CHAT_LOG_CSV = "chat_logs.csv"

# ------------------- UTILITY -------------------
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

# ------------------- CHATBOT -------------------
def bot_reply(text):
    t = (text or "").lower().strip()
    crisis_words = ["suicide", "kill myself", "die", "end my life", "want to die", "hopeless", "give up", "self harm", "cut myself"]
    problem_words = ["stress", "anxiety", "sad", "depressed", "panic", "overwhelmed"]

    if any(word in t for word in crisis_words):
        return ("⚠ You might be in serious danger.<br>"
                "📞 <b>AASRA:</b> 91-9820466726<br>"
                "📞 <b>Snehi:</b> +91-9582208181<br>")

    if any(word in t for word in problem_words):
        return "Thank you for sharing. You can now choose: Peer Chat, Resources, or Book a Counseling Session."

    if not t:
        return "Hey — say anything if you want to talk."

    return "I hear you. Can you tell me a bit more about how you're feeling?"

# ------------------- ROUTES -------------------
@app.route("/")
def home():
    anon = get_anon()
    return f"""
    <div style="font-family:Arial;margin:40px auto;max-width:700px;">
      <h2 style="color:#2b6e4f;">Digital Wellness Assistant</h2>
      <p>Welcome! Your anonymous ID is <b>{escape(anon)}</b>.</p>
      <a href="/chat" style="padding:8px 10px;background:#2b6e4f;color:white;text-decoration:none;border-radius:4px;">Start Chatbot</a>
    </div>
    """

@app.route("/chat")
def chat():
    anon = get_anon()
    return f"""
    <html>
    <head><meta charset="utf-8"><title>Chatbot</title></head>
    <body style="font-family:Arial;max-width:700px;margin:20px auto;">
      <h3 style="color:#2b6e4f;">Chat with Wellness Assistant</h3>
      <div id="chatbox" style="border:1px solid #ccc;padding:10px;height:350px;overflow:auto;background:white;"></div>
      <form id="chatform" style="margin-top:10px;">
        <input id="message" placeholder="Type your message..." style="width:75%;padding:8px;border:1px solid #ccc;border-radius:4px;">
        <button type="submit" style="padding:8px;background:#2b6e4f;color:white;border:none;border-radius:4px;">Send</button>
      </form>
      <script>
        const anon = "{anon}";
        const chatbox = document.getElementById('chatbox');
        const form = document.getElementById('chatform');
        const msgInput = document.getElementById('message');

        function append(who, text) {{
          const div = document.createElement('div');
          div.style.margin = '6px 0';
          div.innerHTML = "<b>" + who + ":</b> " + text;
          chatbox.appendChild(div);
          chatbox.scrollTop = chatbox.scrollHeight;
        }}

        form.addEventListener('submit', async function(e) {{
          e.preventDefault();
          const text = msgInput.value.trim();
          if (!text) return;
          append('You', text);
          msgInput.value = '';
          const res = await fetch('/chatbot', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{anon_id: anon, message: text}})
          }});
          const data = await res.json();
          append('Bot', data.reply);
          if (data.reply.includes("You can now choose")) {{
            setTimeout(function() {{ window.location.href = '/help'; }}, 1000);
          }}
        }});
      </script>
    </body>
    </html>
    """

@app.route("/help")
def help_page():
    anon = get_anon()
    return f"""
    <div style="font-family:Arial;max-width:700px;margin:40px auto;text-align:center;">
      <h3 style="color:#2b6e4f;">Support Options</h3>
      <p>Hi <b>{escape(anon)}</b>, choose what you want to do:</p>
      <div style="display:flex;flex-direction:column;gap:12px;max-width:400px;margin:20px auto;">
        <a href="/peer" style="padding:10px;background:#6aa76a;color:white;text-decoration:none;border-radius:5px;">💬 Peer-to-Peer Chat</a>
        <a href="/resources" style="padding:10px;background:#8fbf8f;color:white;text-decoration:none;border-radius:5px;">📚 Wellness Resources</a>
        <a href="/book" style="padding:10px;background:#a7d6a7;color:white;text-decoration:none;border-radius:5px;">🧑‍⚕ Book a Counseling Session</a>
        <a href="/helpline" style="padding:10px;background:#e57373;color:white;text-decoration:none;border-radius:5px;">☎ Immediate Helpline</a>
      </div>
      <a href="/chat" style="color:#2b6e4f;">← Back to Chatbot</a>
    </div>
    """

@app.route("/peer")
def peer():
    anon = get_anon()
    return f"""
    <div style="font-family:Arial;max-width:700px;margin:40px auto;text-align:center;">
      <h3 style="color:#2b6e4f;">Peer Support Chat</h3>
      <p>Welcome, <b>{escape(anon)}</b>. A peer will be connected soon.</p>
      <p style="color:#666;">(Demo placeholder — peer connection not active yet.)</p>
      <a href="/help" style="color:#2b6e4f;">← Back to Help Menu</a>
    </div>
    """

@app.route("/resources")
def resources():
    return """
    <div style="font-family:Arial;max-width:700px;margin:40px auto;">
      <h3 style="color:#2b6e4f;">Wellness Resources</h3>
      <ul>
        <li><a href="https://www.healthline.com/health/grounding-techniques" target="_blank">5-Min Grounding Trick</a></li>
        <li><a href="https://www.youtube.com/watch?v=inpok4MKVLM" target="_blank">Short Guided Calm</a></li>
        <li><a href="https://www.youtube.com/watch?v=hnpQrMqDoqE" target="_blank">Stress Basics</a></li>
      </ul>
      <a href="/help" style="color:#2b6e4f;">← Back to Help Menu</a>
    </div>
    """

@app.route("/book", methods=["GET", "POST"])
def book():
    anon = get_anon()
    state = load_state()

    if request.method == "POST":
        date_time = request.form.get("datetime", "").strip()
        if date_time:
            state["bookings"].append({"anon_id": anon, "datetime": date_time})
            save_state(state)
            return f"<p>✅ Session booked for {escape(date_time)}.</p><a href='/help'>← Back to Help Menu</a>"
        return redirect(url_for("book"))

    return f"""
    <div style="font-family:Arial;max-width:700px;margin:40px auto;text-align:center;">
      <h3 style="color:#2b6e4f;">Book a Counseling Session</h3>
      <form method="POST">
        <input name="datetime" placeholder="YYYY-MM-DD HH:MM" style="padding:8px;width:60%;border-radius:4px;border:1px solid #ccc;">
        <button type="submit" style="padding:8px;background:#2b6e4f;color:white;border:none;border-radius:4px;">Confirm Booking</button>
      </form>
      <a href="/help" style="color:#2b6e4f;">← Back to Help Menu</a>
    </div>
    """

@app.route("/helpline")
def helpline():
    return """
    <div style="font-family:Arial;max-width:700px;margin:40px auto;">
      <h3 style="color:#e57373;">Immediate Helplines</h3>
      <p>📞 <b>AASRA:</b> 91-9820466726<br>📞 <b>Snehi:</b> +91-9582208181</p>
      <a href="/help" style="color:#2b6e4f;">← Back to Help Menu</a>
    </div>
    """

@app.route("/chatbot", methods=["POST"])
def chatbot():
    payload = request.get_json() or {}
    message = (payload.get("message") or "").strip()
    anon = payload.get("anon_id") or get_anon()
    reply = bot_reply(message)
    if message:
        log_chat(anon, "user", message)
    log_chat(anon, "bot", reply)
    return jsonify({"reply": reply})

# ------------------- RUN -------------------
if _name_ == "_main_":
    ensure_chat_log()
    print("✅ Running Wellness Chatbot → http://127.0.0.1:5000")
    app.run(debug=True)



