"""
パルスサーベイシステム - Web API
Flask ベースのサーベイ回答・管理API
"""
from flask import Flask, request, jsonify, redirect
from datetime import datetime

import config
import database as db
import survey_manager as sm
import email_sender as mailer

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # 日本語対応


# ─── 従業員向け: サーベイ回答 ─────────────────────

@app.route("/survey/<token>", methods=["GET"])
def survey_page(token):
    """
    サーベイ回答ページ（フロントエンドへリダイレクト）
    実運用では React のページに token をクエリパラメータとして渡す
    """
    info = sm.validate_token(token)
    if not info:
        return jsonify({"error": "このリンクは無効または期限切れです"}), 400

    # 本番では React アプリにリダイレクト
    # return redirect(f"{config.BASE_URL}/app/survey?token={token}")

    # 開発用: サーベイ情報をJSON返却
    return jsonify({
        "status": "valid",
        "employee_name": info["emp_name"],
        "survey_title": info["survey_title"],
        "deadline": info["deadline"],
        "questions": config.SURVEY_QUESTIONS,
        "extra_question": {
            "title": info["extra_question_title"],
            "description": info["extra_question_description"],
        } if info["extra_question_title"] else None,
    })


@app.route("/api/survey/submit", methods=["POST"])
def submit_survey():
    """
    サーベイ回答の送信
    POST Body:
    {
        "token": "xxx",
        "work_satisfaction": 4,
        "relationships": 3,
        "health": 5,
        "extra_answer": null,
        "comment": "自由コメント"
    }
    """
    data = request.get_json()
    if not data or "token" not in data:
        return jsonify({"error": "トークンが必要です"}), 400

    required = ["work_satisfaction", "relationships", "health"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} が必要です"}), 400

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
            "message": "回答ありがとうございました！",
            **result,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/survey/validate/<token>", methods=["GET"])
def validate_survey_token(token):
    """トークンの有効性を確認"""
    info = sm.validate_token(token)
    if not info:
        return jsonify({"valid": False, "error": "無効または期限切れのリンクです"}), 400

    return jsonify({
        "valid": True,
        "employee_name": info["emp_name"],
        "survey_title": info["survey_title"],
        "deadline": info["deadline"],
    })


# ─── 管理者向け: サーベイ管理 API ─────────────────

@app.route("/api/admin/surveys", methods=["GET"])
def list_surveys():
    """サーベイ一覧"""
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM surveys ORDER BY year_month DESC").fetchall()
        return jsonify([dict(r) for r in rows])


@app.route("/api/admin/surveys", methods=["POST"])
def create_survey():
    """
    新規サーベイ作成
    POST Body:
    {
        "year_month": "2026-03",
        "title": "2026年3月度 パルスサーベイ",
        "start_date": "2026-03-01",
        "deadline": "2026-03-14",
        "extra_question_title": "追加質問タイトル（任意）",
        "extra_question_description": "追加質問の説明（任意）"
    }
    """
    data = request.get_json()
    required = ["year_month", "title", "start_date", "deadline"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} が必要です"}), 400

    survey_id = db.create_survey(
        year_month=data["year_month"],
        title=data["title"],
        start_date=data["start_date"],
        deadline=data["deadline"],
        extra_question_title=data.get("extra_question_title"),
        extra_question_desc=data.get("extra_question_description"),
    )
    return jsonify({"status": "success", "survey_id": survey_id})


@app.route("/api/admin/surveys/<int:survey_id>/prepare", methods=["POST"])
def prepare_survey(survey_id):
    """サーベイの配信準備（トークン生成）"""
    try:
        result = sm.prepare_survey(survey_id)
        return jsonify({
            "status": "success",
            "message": f"{result['total']}名分のトークンを生成しました",
            "total": result["total"],
            "sample_urls": [t["url"] for t in result["tokens"][:3]],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/admin/surveys/<int:survey_id>/send", methods=["POST"])
def send_invites(survey_id):
    """案内メールを送信"""
    result = mailer.send_survey_invites(survey_id)
    return jsonify({
        "status": "success",
        "message": f"{result['sent']}件の案内メールを送信しました",
        **result,
    })


@app.route("/api/admin/surveys/<int:survey_id>/remind", methods=["POST"])
def send_remind(survey_id):
    """未回答者にリマインドメールを送信"""
    result = mailer.send_reminders(survey_id)
    return jsonify({
        "status": "success",
        "message": f"{result['sent']}件のリマインドを送信しました",
        **result,
    })


@app.route("/api/admin/surveys/<int:survey_id>/close", methods=["POST"])
def close_survey(survey_id):
    """サーベイを締め切る"""
    db.close_survey(survey_id)
    return jsonify({"status": "success", "message": "サーベイを締め切りました"})


@app.route("/api/admin/surveys/<int:survey_id>/stats", methods=["GET"])
def survey_stats(survey_id):
    """サーベイの集計結果"""
    stats = db.get_survey_stats(survey_id)
    return jsonify(stats)


@app.route("/api/admin/surveys/<int:survey_id>/progress", methods=["GET"])
def survey_progress(survey_id):
    """サーベイの進捗状況"""
    progress = sm.get_survey_progress(survey_id)
    return jsonify(progress)


@app.route("/api/admin/surveys/<int:survey_id>/responses", methods=["GET"])
def survey_responses(survey_id):
    """サーベイの全回答"""
    responses = db.get_responses(survey_id)
    return jsonify(responses)


# ─── 管理者向け: 従業員管理 ──────────────────────

@app.route("/api/admin/employees", methods=["GET"])
def list_employees():
    """従業員一覧"""
    employees = db.get_active_employees()
    return jsonify(employees)


@app.route("/api/admin/employees", methods=["POST"])
def add_employee():
    """従業員を追加"""
    data = request.get_json()
    emp_id = db.add_employee(
        name=data["name"],
        email=data["email"],
        department=data["department"],
        join_year=data.get("join_year"),
    )
    return jsonify({"status": "success", "employee_id": emp_id})


@app.route("/api/admin/employees/import", methods=["POST"])
def import_employees():
    """
    従業員一括登録
    POST Body: {"employees": [{"name": ..., "email": ..., "department": ..., "join_year": ...}, ...]}
    """
    data = request.get_json()
    count = db.import_employees_bulk(data.get("employees", []))
    return jsonify({"status": "success", "imported": count})


@app.route("/api/admin/employees/<int:employee_id>", methods=["GET"])
def employee_detail(employee_id):
    """従業員詳細（履歴含む）"""
    emp = db.get_employee_by_id(employee_id)
    if not emp:
        return jsonify({"error": "従業員が見つかりません"}), 404

    history = db.get_employee_history(employee_id)
    notes = db.get_follow_up_notes(employee_id)
    return jsonify({"employee": emp, "history": history, "notes": notes})


@app.route("/api/admin/employees/<int:employee_id>/notes", methods=["POST"])
def add_note(employee_id):
    """対応記録を追加"""
    data = request.get_json()
    note_id = db.add_follow_up_note(
        employee_id=employee_id,
        author=data["author"],
        note=data["note"],
        survey_id=data.get("survey_id"),
        action_type=data.get("action_type", "memo"),
    )
    return jsonify({"status": "success", "note_id": note_id})


# ─── ヘルスチェック ──────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app": config.APP_NAME, "time": datetime.now().isoformat()})


# ─── 起動 ─────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print(f"\n{'='*50}")
    print(f"  {config.APP_NAME}")
    print(f"  URL: {config.BASE_URL}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
