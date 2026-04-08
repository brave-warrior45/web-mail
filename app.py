from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)
API_BASE = 'https://www.1secmail.com/api/v1/'

@app.route('/')
def index():
    return render_template('index.html')

# --- Proxy Routes for the API ---

@app.route('/api/generate')
def generate():
    res = requests.get(f"{API_BASE}?action=genRandomMailbox&count=1")
    return jsonify(res.json())

@app.route('/api/messages')
def get_messages():
    login = request.args.get('login')
    domain = request.args.get('domain')
    res = requests.get(f"{API_BASE}?action=getMessages&login={login}&domain={domain}")
    return jsonify(res.json())

@app.route('/api/read')
def read_message():
    login = request.args.get('login')
    domain = request.args.get('domain')
    msg_id = request.args.get('id')
    res = requests.get(f"{API_BASE}?action=readMessage&login={login}&domain={domain}&id={msg_id}")
    return jsonify(res.json())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
