from flask import Flask, render_template, request, jsonify, session
import requests
import random
import string
import os
from pymongo import MongoClient

app = Flask(__name__)
# Secret key for secure login sessions
app.secret_key = os.environ.get('SECRET_KEY', 'default_cyber_secret_123')

# MongoDB Connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/').strip('"').strip("'")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.tempmail_db
    accounts_col = db.saved_accounts
except Exception as e:
    print(f"CRITICAL MongoDB connection error: {e}")

API_BASE = 'https://api.mail.gw'
ADMIN_USER = os.environ.get('ADMIN_USER', 'cyber')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '1948s')
REQ_TIMEOUT = 10  # Stop Gunicorn from freezing if mail.gw is slow

def is_admin():
    return session.get('logged_in') is True

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@app.route('/')
def index():
    return render_template('index.html')

# --- Admin Auth Routes ---

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        session['logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({"success": True})

@app.route('/api/auth/status')
def auth_status():
    return jsonify({"logged_in": is_admin()})

# --- Database Routes ---

@app.route('/api/db/accounts', methods=['GET'])
def get_accounts():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    accounts = list(accounts_col.find({}, {'_id': 0})) 
    return jsonify(accounts)

@app.route('/api/db/accounts', methods=['POST'])
def save_account():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not accounts_col.find_one({"email": data.get('email')}):
        accounts_col.insert_one({
            "email": data.get('email'),
            "password": data.get('password'),
            "token": data.get('token')
        })
    return jsonify({"success": True})

@app.route('/api/db/accounts', methods=['DELETE'])
def delete_account():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    accounts_col.delete_one({"email": data.get('email')})
    return jsonify({"success": True})

# --- Proxy Routes for Mail API ---

@app.route('/api/generate')
def generate():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    try:
        dom_res = requests.get(f"{API_BASE}/domains", timeout=REQ_TIMEOUT)
        dom_res.raise_for_status()
        domain = dom_res.json().get('hydra:member', [])[0]['domain']

        username = generate_random_string(12)
        password = generate_random_string(16)
        email = f"{username}@{domain}"
        
        acc_payload = {"address": email, "password": password}
        requests.post(f"{API_BASE}/accounts", json=acc_payload, timeout=REQ_TIMEOUT).raise_for_status()

        tok_res = requests.post(f"{API_BASE}/token", json=acc_payload, timeout=REQ_TIMEOUT)
        tok_res.raise_for_status()
        
        return jsonify({"email": email, "token": tok_res.json()['token'], "password": password})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    try:
        acc_payload = {"address": data.get('address'), "password": data.get('password')}
        tok_res = requests.post(f"{API_BASE}/token", json=acc_payload, timeout=REQ_TIMEOUT)
        tok_res.raise_for_status()
        return jsonify({"email": data.get('address'), "token": tok_res.json()['token'], "password": data.get('password')})
    except Exception as e:
        return jsonify({"error": "Invalid email/password or account expired."}), 401

@app.route('/api/messages')
def get_messages():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    token = request.args.get('token')
    try:
        res = requests.get(f"{API_BASE}/messages", headers={"Authorization": f"Bearer {token}"}, timeout=REQ_TIMEOUT)
        res.raise_for_status()
        return jsonify([
            {"id": msg['id'], "from": msg.get('from', {}).get('address', 'Unknown') if isinstance(msg.get('from'), dict) else msg.get('from', 'Unknown'), 
             "subject": msg.get('subject', '(No Subject)'), "date": msg.get('createdAt', '')} 
            for msg in res.json().get('hydra:member', [])
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/read')
def read_message():
    if not is_admin(): return jsonify({"error": "Unauthorized"}), 401
    token = request.args.get('token')
    msg_id = request.args.get('id')
    try:
        res = requests.get(f"{API_BASE}/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"}, timeout=REQ_TIMEOUT)
        res.raise_for_status()
        msg = res.json()
        html_body = msg.get('html', [''])[0] if isinstance(msg.get('html'), list) and msg.get('html') else msg.get('html', '')
        return jsonify({
            "subject": msg.get('subject', ''), "from": msg.get('from', {}).get('address', 'Unknown') if isinstance(msg.get('from'), dict) else msg.get('from', 'Unknown'),
            "date": msg.get('createdAt', ''), "textBody": msg.get('text', ''), "htmlBody": html_body
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
