from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import os

import config
import database as db
import survey_manager as sm
import email_sender as mailer

# ─────────────────────────────
# Flask 初期化（最初！）
# ─────────────────────────────
app = Flask(
    __name__,
    static_folder=None  # ← これが超重要
)
app.config["JSON_AS_ASCII"] = False

# ─────────────────────────────
# API（Reactより先に定義）
# ─────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "app": config.APP_NAME,
        "time": datetime.now().isoformat()
    })


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
        return jsonify({"status": "success", **result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/survey/validate/<token>")
def validate_survey_token(token):
    info = sm.validate_token(token)
    if not info:
        return jsonify({"valid": False}), 400
    return jsonify({
        "valid": True,
        "survey_title": info["survey_title"],
        "deadline": info["deadline"],
    })


# （他の /api/... ルートもここに並べる）
# ─────────────────────────────


# ─────────────────────────────
# React build 配信（最後！）
# ─────────────────────────────

REACT_BUILD_DIR = os.path.join(os.getcwd(), "frontend", "build")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(
        os.path.join(REACT_BUILD_DIR, "static"),
        filename
    )

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(REACT_BUILD_DIR, path)):
        return send_from_directory(REACT_BUILD_DIR, path)
    else:
        return send_from_directory(REACT_BUILD_DIR, "index.html")


# ─────────────────────────────
# 起動
# ─────────────────────────────
if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000)
