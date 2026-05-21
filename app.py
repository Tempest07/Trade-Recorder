from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__, static_folder='.', static_url_path='')
DATA_FILE = 'data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"windows": [], "nextId": 1}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# API：获取全部数据
@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(load_data())

# API：保存全部数据
@app.route('/api/data', methods=['POST'])
def update_data():
    data = request.get_json()
    save_data(data)
    return jsonify({"status": "ok"})

# 提供前端页面（访问根路径或 /index.html）
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/index.html')
def index_page():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render 必须用环境变量 PORT
    app.run(host='0.0.0.0', port=port)
