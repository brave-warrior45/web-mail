from flask import Flask, render_template, request, jsonify
import requests
import random
import string
import os

app = Flask(__name__)
API_BASE = 'https://api.mail.gw'

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@app.route('/')
def index():
    return render_template('index.html')

# --- Proxy Routes for the NEW API ---

@app.route('/api/generate')
def generate():
    try:
        # 1. Get available active domains
        dom_res = requests.get(f"{API_BASE}/domains")
        dom_res.raise_for_status()
        domains = dom_res.json().get('hydra:member', [])
        if not domains:
            return jsonify({"error": "No domains available"}), 500
        domain = domains[0]['domain']

        # 2. Generate random credentials and create account
        username = generate_random_string(12)
        password = generate_random_string(16)
        email = f"{username}@{domain}"
        
        acc_payload = {"address": email, "password": password}
        acc_res = requests.post(f"{API_BASE}/accounts", json=acc_payload)
        acc_res.raise_for_status()

        # 3. Authenticate to get the JWT access token
        tok_res = requests.post(f"{API_BASE}/token", json=acc_payload)
        tok_res.raise_for_status()
        token = tok_res.json()['token']

        return jsonify({
            "email": email,
            "token": token
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages')
def get_messages():
    token = request.args.get('token')
    if not token:
        return jsonify([]), 200
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{API_BASE}/messages", headers=headers)
        res.raise_for_status()
        messages = res.json().get('hydra:member', [])
        
        # Format for the frontend UI
        formatted_msgs = []
        for msg in messages:
            sender = msg.get('from', {})
            sender_address = sender.get('address', 'Unknown') if isinstance(sender, dict) else sender
            formatted_msgs.append({
                "id": msg['id'],
                "from": sender_address,
                "subject": msg.get('subject', '(No Subject)'),
                "date": msg.get('createdAt', '')
            })
        return jsonify(formatted_msgs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/read')
def read_message():
    token = request.args.get('token')
    msg_id = request.args.get('id')
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{API_BASE}/messages/{msg_id}", headers=headers)
        res.raise_for_status()
        msg = res.json()
        
        sender = msg.get('from', {})
        sender_address = sender.get('address', 'Unknown') if isinstance(sender, dict) else sender
        
        # mail.gw stores HTML body in a list
        html_body = msg.get('html', [''])[0] if isinstance(msg.get('html'), list) and msg.get('html') else msg.get('html', '')

        return jsonify({
            "subject": msg.get('subject', ''),
            "from": sender_address,
            "date": msg.get('createdAt', ''),
            "textBody": msg.get('text', ''),
            "htmlBody": html_body
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
