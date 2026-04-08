from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)
API_BASE = 'https://www.1secmail.com/api/v1/'

# Fake browser headers to bypass bot-protection/Cloudflare
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
}

@app.route('/')
def index():
    return render_template('index.html')

# --- Proxy Routes for the API ---

@app.route('/api/generate')
def generate():
    try:
        res = requests.get(f"{API_BASE}?action=genRandomMailbox&count=1", headers=HEADERS)
        if res.status_code != 200:
            return jsonify({"error": "API blocked the request", "status": res.status_code}), 500
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages')
def get_messages():
    login = request.args.get('login')
    domain = request.args.get('domain')
    try:
        res = requests.get(f"{API_BASE}?action=getMessages&login={login}&domain={domain}", headers=HEADERS)
        if res.status_code != 200:
            return jsonify([]), 200 # Return empty inbox on error
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/read')
def read_message():
    login = request.args.get('login')
    domain = request.args.get('domain')
    msg_id = request.args.get('id')
    try:
        res = requests.get(f"{API_BASE}?action=readMessage&login={login}&domain={domain}&id={msg_id}", headers=HEADERS)
        if res.status_code != 200:
            return jsonify({"error": "Failed to read message"}), 500
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
