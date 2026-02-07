from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import os

import config
import database as db
import survey_manager as sm
import email_sender as mailer

# ============================================================
# Flask 初期化
# ============================================================
app = Flask(__name__, static_folder=None)
app.config["JSON_AS_ASCII"] = False

# ★ gunicorn 起動でも必ず実行される
db.init_db()

# このファイル自身の場所を基準にする（Render対策）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REACT_BUILD_DIR = os.path.join(BASE_DIR, "frontend", "build")

# ============================================================
# ヘルスチェック
# ============================================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "app": config.APP_NAME,
        "time": datetime.now().isoformat()
    })

# ============================================================
# 回答者向け API
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
        )
        return jsonify({
            "status": "success",
            "message": "回答ありがとうございました",
            **result
        })
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
# 管理者向け API
# ============================================================

# サーベイ一覧
@app.route("/api/admin/surveys", methods=["GET"])
def list_surveys():
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM surveys ORDER BY year_month DESC"
        ).fetchall()
        return jsonify([dict(r) for r in rows])

# トークン生成（本番用）
@app.route("/api/admin/surveys/<int:survey_id>/prepare", methods=["POST"])
def prepare_survey(survey_id):
    try:
        result = sm.prepare_survey(survey_id)
        return jsonify({
            "status": "success",
            "total": result["total"],
            "sample_urls": [t["url"] for t in result["tokens"][:5]]
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# 回答一覧
@app.route("/api/admin/surveys/<int:survey_id>/responses", methods=["GET"])
def survey_responses(survey_id):
    responses = db.get_responses(survey_id)
    return jsonify(responses)

# 集計
@app.route("/api/admin/surveys/<int:survey_id>/stats", methods=["GET"])
def survey_stats(survey_id):
    stats = db.get_survey_stats(survey_id)
    return jsonify(stats)

# 進捗
@app.route("/api/admin/surveys/<int:survey_id>/progress", methods=["GET"])
def survey_progress(survey_id):
    progress = sm.get_survey_progress(survey_id)
    return jsonify(progress)

# ============================================================
# React SPA 配信
# ============================================================

# ① トップページ
@app.route("/")
def index():
    return send_from_directory(REACT_BUILD_DIR, "index.html")

# ② static ファイル
@app.route("/static/<path:filename>")
def react_static(filename):
    return send_from_directory(
        os.path.join(REACT_BUILD_DIR, "static"),
        filename
    )

# ③ React Router 対応（/survey/<token> など）
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
