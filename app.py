from flask import Flask, jsonify, request, render_template
import qrcode
import os
import socket
import json
from threading import Lock
from datetime import datetime, timedelta

app = Flask(__name__)

QUEUE_FILE = "token_queue.json"
queue = []
current_token = {'token': 0, 'name': '', 'age': '', 'time': ''}

lock = Lock()

# ---------------- FILE ----------------
def save_queue():
    with open(QUEUE_FILE, 'w') as f:
        json.dump({'queue': queue, 'current_token': current_token}, f)

def load_queue():
    global queue, current_token
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f:
                data = json.load(f)
                queue = data.get('queue', [])
                current_token = data.get('current_token', {'token': 0, 'name': '', 'age': '', 'time': ''})
    except:
        pass

load_queue()
os.makedirs("static", exist_ok=True)

# ---------------- REMOVE EXPIRED ----------------
def remove_expired_tokens():
    global queue
    new_queue = []

    for customer in queue:
        token_time = datetime.strptime(customer['time'], "%Y-%m-%d %H:%M:%S")

        # ⏰ 2 minutes expiry
        if datetime.now() - token_time < timedelta(minutes=2):
            new_queue.append(customer)

    queue = new_queue

# ---------------- IP ----------------
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return socket.gethostbyname(socket.gethostname())

LOCAL_IP = get_local_ip()

print("\n🌐 SERVER STARTED")
print(f"👉 Laptop: http://127.0.0.1:5000")
print(f"👉 Mobile: http://{LOCAL_IP}:5000")

# ---------------- QR ----------------
def generate_qr():
    url = f"http://{LOCAL_IP}:5000/get_token"
    img = qrcode.make(url)
    img.save("static/qr.png")
    print(f"📱 QR URL: {url}")

generate_qr()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------- TOKEN PAGE ----------------
@app.route('/get_token')
def get_token():
    return """
    <html><body style="text-align:center">
    <h2>Enter Details</h2>
    <form action="/generate_token" method="POST">
        Name: <input name="name"><br><br>
        Age: <input name="age" type="number"><br><br>
        <button>Get Token</button>
    </form>
    </body></html>
    """

# ---------------- GENERATE TOKEN ----------------
@app.route('/generate_token', methods=['POST'])
def generate_token():
    name = request.form.get('name')
    age = request.form.get('age')

    with lock:
        load_queue()
        remove_expired_tokens()

        next_token = max([c.get('token', 0) for c in queue] + [current_token['token']]) + 1

        customer = {
            'token': next_token,
            'name': name,
            'age': age,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        queue.append(customer)
        save_queue()

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">
    <script>
    let timeLeft = 120; // 2 minutes

    function startTimer() {{
        let timer = setInterval(function() {{
            let minutes = Math.floor(timeLeft / 60);
            let seconds = timeLeft % 60;

            document.getElementById("timer").innerHTML =
                minutes + "m " + seconds + "s";

            timeLeft--;

            if (timeLeft < 0) {{
                clearInterval(timer);
                document.getElementById("timer").innerHTML = "Expired ❌";
                document.getElementById("timer").style.color = "red";
            }}
        }}, 1000);
    }}
    </script>
    </head>

    <body onload="startTimer()" style="text-align:center;font-family:Arial">
    <h1>🎫 Token {next_token}</h1>
    <h2>{name}</h2>

    <p>⏳ Time Remaining:</p>
    <h2 id="timer" style="color:green;">2m 0s</h2>

    <p>Valid for 2 minutes</p>
    </body>
    </html>
    """

# ---------------- NEXT ----------------
@app.route('/next')
def next():
    with lock:
        load_queue()
        remove_expired_tokens()

        if queue:
            current_token.update(queue.pop(0))
            save_queue()

    return "Next Done"

# ---------------- DISPLAY ----------------
@app.route('/display')
def display():
    load_queue()
    remove_expired_tokens()

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="3"></head>
    <body style="background:black;color:white;text-align:center;font-size:50px">
        <h1>Now Serving</h1>
        <h2>{current_token['token'] or 0}</h2>
        <h3>{current_token['name']}</h3>
    </body>
    </html>
    """

# ---------------- API ----------------
@app.route('/api/status')
def api():
    load_queue()
    remove_expired_tokens()

    return jsonify({
        'queue': len(queue),
        'current': current_token
    })

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)