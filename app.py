from pathlib import Path
from threading import Lock
import json
import os

from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
TEMP_FILE = BASE_DIR / "data.json.tmp"
MAX_WINDOWS = 500
MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 200_000

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
data_lock = Lock()


def empty_data():
    return {"windows": [], "nextId": 1, "updatedAt": None}


def validate_data(data):
    if not isinstance(data, dict) or not isinstance(data.get("windows"), list):
        raise ValueError("请求必须包含 windows 数组")
    if len(data["windows"]) > MAX_WINDOWS:
        raise ValueError(f"窗口数量不能超过 {MAX_WINDOWS}")

    normalized = []
    used_ids = set()
    for item in data["windows"]:
        if not isinstance(item, dict):
            raise ValueError("窗口数据格式不正确")

        record_id = item.get("id")
        title = item.get("title", "")
        content = item.get("content", "")
        if not isinstance(record_id, int) or record_id < 1 or record_id in used_ids:
            raise ValueError("窗口 ID 必须是唯一的正整数")
        if not isinstance(title, str) or len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"标题长度不能超过 {MAX_TITLE_LENGTH} 个字符")
        if not isinstance(content, str) or len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(f"单个窗口内容不能超过 {MAX_CONTENT_LENGTH} 个字符")

        used_ids.add(record_id)
        normalized.append(
            {
                "id": record_id,
                "title": title,
                "content": content,
                "collapsed": bool(item.get("collapsed", False)),
                "createdAt": item.get("createdAt") if isinstance(item.get("createdAt"), str) else None,
                "updatedAt": item.get("updatedAt") if isinstance(item.get("updatedAt"), str) else None,
            }
        )

    highest_id = max(used_ids, default=0)
    next_id = data.get("nextId", highest_id + 1)
    if not isinstance(next_id, int) or next_id <= highest_id:
        next_id = highest_id + 1

    return {
        "windows": normalized,
        "nextId": next_id,
        "updatedAt": data.get("updatedAt") if isinstance(data.get("updatedAt"), str) else None,
    }


def load_data():
    if not DATA_FILE.exists():
        return empty_data()
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return validate_data(json.load(file))


def save_data(data):
    normalized = validate_data(data)
    with data_lock:
        with TEMP_FILE.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        TEMP_FILE.replace(DATA_FILE)
    return normalized


@app.get("/api/data")
def get_data():
    try:
        return jsonify(load_data())
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return jsonify({"error": f"读取数据失败：{error}"}), 500


@app.post("/api/data")
def update_data():
    try:
        data = request.get_json()
        save_data(data)
        return jsonify({"status": "ok"})
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return jsonify({"error": str(error)}), 400
    except OSError as error:
        return jsonify({"error": f"保存数据失败：{error}"}), 500


@app.errorhandler(413)
def payload_too_large(_error):
    return jsonify({"error": "提交的数据过大"}), 413


@app.get("/")
@app.get("/index.html")
def index():
    return send_from_directory(BASE_DIR, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
