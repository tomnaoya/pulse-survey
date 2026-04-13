from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
from functools import wraps
import os
import base64

import config
import database as db
import survey_manager as sm

# ============================================================
# Flask 初期化
# ============================================================
app = Flask(__name__, static_folder=None)
app.config["JSON_AS_ASCII"] = False

db.init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REACT_BUILD_DIR = os.path.join(BASE_DIR, "frontend", "build")

def _seed_persistent_db():
    bundled_db = os.path.join(BASE_DIR, "survey.db")
    if bundled_db == config.DATABASE_PATH:
        return
    if not os.path.exists(bundled_db):
        return
    with db.get_db() as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM employees").fetchone()["c"]
        if count > 0:
            return
    import sqlite3
    print("[SEED] 永続DBが空のため、同梱DBからデータを移行します...")
    src = sqlite3.connect(bundled_db)
    src.row_factory = sqlite3.Row
    with db.get_db() as conn:
        for row in src.execute("SELECT * FROM employees").fetchall():
            conn.execute(
                "INSERT OR IGNORE INTO employees (id, name, email, department, join_year, is_active) VALUES (?,?,?,?,?,?)",
                (row["id"], row["name"], row["email"], row["department"], row["join_year"], row["is_active"]),
            )
        for row in src.execute("SELECT * FROM surveys").fetchall():
            conn.execute(
                "INSERT OR IGNORE INTO surveys (id, year_month, title, start_date, deadline, extra_question_title, extra_question_description, status) VALUES (?,?,?,?,?,?,?,?)",
                (row["id"], row["year_month"], row["title"], row["start_date"], row["deadline"], row["extra_question_title"], row["extra_question_description"], row["status"]),
            )
        for row in src.execute("SELECT * FROM survey_tokens").fetchall():
            conn.execute(
                "INSERT OR IGNORE INTO survey_tokens (id, survey_id, employee_id, token, is_used, sent_at, reminded_at, expires_at) VALUES (?,?,?,?,?,?,?,?)",
                (row["id"], row["survey_id"], row["employee_id"], row["token"], row["is_used"], row["sent_at"], row["reminded_at"], row["expires_at"]),
            )
    src.close()
    print("[SEED] データ移行完了")

_seed_persistent_db()

# ============================================================
# Basic認証（管理者向けAPIの保護）
# ============================================================
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "changeme")

def require_admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return jsonify({"error": "認証が必要です"}), 401, {"WWW-Authenticate": 'Basic realm="Admin"'}
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            user, password = decoded.split(":", 1)
            if user != ADMIN_USER or password != ADMIN_PASS:
                raise ValueError
        except Exception:
            return jsonify({"error": "認証に失敗しました"}), 401, {"WWW-Authenticate": 'Basic realm="Admin"'}
        return f(*args, **kwargs)
    return decorated

# ============================================================
# ヘルスチェック
# ============================================================
@app.route("/health", methods=["GET"])
def health():
    db_path = config.DATABASE_PATH
    db_exists = os.path.exists(db_path)
    db_size = os.path.getsize(db_path) if db_exists else 0
    survey_count = 0
    employee_count = 0
    token_count = 0
    try:
        with db.get_db() as conn:
            survey_count = conn.execute("SELECT COUNT(*) as c FROM surveys").fetchone()["c"]
            employee_count = conn.execute("SELECT COUNT(*) as c FROM employees").fetchone()["c"]
            token_count = conn.execute("SELECT COUNT(*) as c FROM survey_tokens").fetchone()["c"]
    except Exception as e:
        pass
    return jsonify({
        "status": "ok",
        "app": config.APP_NAME,
        "time": datetime.now().isoformat(),
        "db_path": db_path,
        "db_exists": db_exists,
        "db_size_bytes": db_size,
        "surveys": survey_count,
        "employees": employee_count,
        "tokens": token_count,
        "cwd": os.getcwd(),
    })

# ============================================================
# 回答者向け API（認証不要）
# ============================================================
@app.route("/api/survey/submit", methods=["POST"])
def submit_survey():
    data = request.get_json()
    if not data or "token" not in data:
        return jsonify({"error": "トークンが必要です"}), 400
    try:
        result = sm.submit_response(
            token=data["token"],
            work=float(data["work_satisfaction"]),
            relationships=float(data["relationships"]),
            health=float(data["health"]),
            extra=float(data["extra_answer"]) if data.get("extra_answer") else None,
            comment=data.get("comment", ""),
            interview_request=data.get("interview_request"),
        )
        return jsonify({"status": "success", "message": "回答ありがとうございました", **result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/survey/validate/<token>", methods=["GET"])
def validate_survey_token(token):
    info = sm.validate_token(token)
    if not info:
        return jsonify({"valid": False}), 400
    return jsonify({
        "valid": True,
        "employee_name": info["emp_name"],
        "survey_title": info["survey_title"],
        "deadline": info["deadline"],
    })

# ============================================================
# 管理者向け API（Basic認証必須）
# ============================================================
@app.route("/api/admin/surveys", methods=["GET"])
@require_admin_auth
def list_surveys():
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM surveys ORDER BY year_month DESC").fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/admin/surveys/<int:survey_id>/prepare", methods=["POST"])
@require_admin_auth
def prepare_survey(survey_id):
    try:
        result = sm.prepare_survey(survey_id)
        return jsonify({"status": "success", "total": result["total"], "sample_urls": [t["url"] for t in result["tokens"][:5]]})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/admin/surveys/<int:survey_id>/responses", methods=["GET"])
@require_admin_auth
def survey_responses(survey_id):
    return jsonify(db.get_responses(survey_id))

@app.route("/api/admin/surveys/<int:survey_id>/stats", methods=["GET"])
@require_admin_auth
def survey_stats(survey_id):
    return jsonify(db.get_survey_stats(survey_id))

@app.route("/api/admin/surveys/<int:survey_id>/progress", methods=["GET"])
@require_admin_auth
def survey_progress(survey_id):
    return jsonify(sm.get_survey_progress(survey_id))

# ============================================================
# React SPA 配信
# ============================================================
@app.route("/")
def index():
    return send_from_directory(REACT_BUILD_DIR, "index.html")

@app.route("/static/<path:filename>")
def react_static(filename):
    return send_from_directory(os.path.join(REACT_BUILD_DIR, "static"), filename)

@app.route("/<path:path>")
def react_catch_all(path):
    file_path = os.path.join(REACT_BUILD_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(REACT_BUILD_DIR, path)
    return send_from_directory(REACT_BUILD_DIR, "index.html")

# ============================================================
# 起動
# ============================================================
if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000)
