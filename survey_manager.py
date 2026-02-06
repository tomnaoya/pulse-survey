"""
トークン生成・サーベイ配信管理モジュール
従業員ごとにユニークURLを生成し、メールで配信する
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import config
import database as db


def generate_token(employee_id: int, survey_id: int) -> str:
    """
    従業員×サーベイごとにユニークなトークンを生成
    - URLセーフな32文字のランダム文字列
    - HMACで署名して改ざん防止
    """
    random_part = secrets.token_urlsafe(24)
    payload = f"{employee_id}:{survey_id}:{random_part}"
    signature = hmac.new(
        config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:12]
    return f"{random_part}{signature}"


def build_survey_url(token: str) -> str:
    """回答用URLを構築"""
    return f"{config.BASE_URL}/survey/{token}"


def prepare_survey(survey_id: int) -> dict:
    """
    サーベイの配信準備
    - 全有効従業員に対してトークンを生成
    - 戻り値: {"total": 生成数, "tokens": [...]}
    """
    survey = db.get_survey(survey_id)
    if not survey:
        raise ValueError(f"サーベイID {survey_id} が見つかりません")

    employees = db.get_active_employees()
    expires_at = (
        datetime.strptime(survey["deadline"], "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d %H:%M:%S")

    tokens = []
    for emp in employees:
        token = generate_token(emp["id"], survey_id)
        token_id = db.save_token(survey_id, emp["id"], token, expires_at)
        tokens.append({
            "token_id": token_id,
            "employee_id": emp["id"],
            "name": emp["name"],
            "email": emp["email"],
            "department": emp["department"],
            "token": token,
            "url": build_survey_url(token),
        })

    db.activate_survey(survey_id)
    print(f"[配信準備] {len(tokens)}名分のトークンを生成しました")
    return {"total": len(tokens), "tokens": tokens}


def validate_token(token: str) -> dict | None:
    """
    トークンを検証し、有効であれば情報を返す
    無効な場合はNone
    """
    info = db.get_token_info(token)
    if not info:
        return None

    # 有効期限チェック
    expires = datetime.strptime(info["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires:
        return None

    # 使用済みチェック
    if info["is_used"]:
        return None

    # サーベイのステータスチェック
    if info["survey_status"] != "active":
        return None

    return info


def submit_response(token: str, work: float, relationships: float,
                    health: float, extra: float = None, comment: str = "") -> dict:
    """
    サーベイ回答を送信
    トークン検証 → 回答保存 → 結果返却
    """
    info = validate_token(token)
    if not info:
        raise ValueError("無効または期限切れのトークンです")

    # スコアの範囲チェック
    for score, name in [(work, "仕事満足度"), (relationships, "人間関係"), (health, "健康")]:
        if not (1 <= score <= 5):
            raise ValueError(f"{name}のスコアは1〜5の範囲で入力してください")

    response_id = db.save_response(
        survey_id=info["survey_id"],
        employee_id=info["employee_id"],
        token_id=info["id"],
        work=work,
        relationships=relationships,
        health=health,
        extra=extra,
        comment=comment,
    )

    return {
        "response_id": response_id,
        "employee_name": info["emp_name"],
        "survey_title": info["survey_title"],
    }


def get_survey_progress(survey_id: int) -> dict:
    """サーベイの進捗状況を取得"""
    stats = db.get_survey_stats(survey_id)
    unreplied = db.get_unreplied_tokens(survey_id)

    return {
        **stats,
        "unreplied": [
            {"name": u["name"], "email": u["email"], "department": u["department"]}
            for u in unreplied
        ],
    }
