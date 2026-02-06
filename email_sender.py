"""
メール配信モジュール
サーベイ案内・リマインド・アラート通知を送信
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import config
import database as db
from survey_manager import build_survey_url


# ─── メールテンプレート ──────────────────────────────

def _invite_template(employee_name: str, survey_url: str, deadline: str, survey_title: str) -> tuple[str, str]:
    """初回案内メールのテンプレート"""
    subject = f"【ご協力のお願い】{survey_title}（所要時間：約1分）"
    body = f"""{employee_name} さん

いつもお疲れさまです。人事部です。

今月のパルスサーベイをお届けします。
3つの質問にお天気マークで答えるだけ、約1分で完了します。

━━━━━━━━━━━━━━━━━━━
▼ 回答はこちらから（ログイン不要）
{survey_url}
━━━━━━━━━━━━━━━━━━━

■ 質問内容
　☀️ 仕事満足度
　🤝 人間関係
　💪 健康

■ 回答期限
　{deadline}

■ 安心ポイント
　・回答は人事担当者のみ閲覧します
　・上長への個人回答の開示は行いません
　・評価に影響することは一切ありません

率直なご回答をお願いいたします。
皆さまの声を活かして、より働きやすい環境をつくっていきます。

──────────────
人事部
※このメールはパルスサーベイシステムから自動送信されています。
"""
    return subject, body


def _remind_template(employee_name: str, survey_url: str, deadline: str, survey_title: str) -> tuple[str, str]:
    """リマインドメールのテンプレート"""
    subject = f"【リマインド】{survey_title}の回答をお願いします（約1分）"
    body = f"""{employee_name} さん

お忙しいところ恐れ入ります。

今月のパルスサーベイがまだ未回答のようです。
お手すきの際にご回答いただけますと幸いです。

▼ 回答はこちら（約1分で完了）
{survey_url}

回答期限：{deadline}

ご不明点がございましたら、人事部までお気軽にお問い合わせください。

──────────────
人事部
"""
    return subject, body


def _alert_template(hr_name: str, alerts: list[dict], survey_title: str) -> tuple[str, str]:
    """人事担当者向けアラート通知のテンプレート"""
    subject = f"【アラート】{survey_title} - {len(alerts)}名のフォローが必要です"

    alert_lines = []
    for a in alerts:
        scores = f"仕事:{a['work_satisfaction']:.1f} 人間関係:{a['relationships']:.1f} 健康:{a['health']:.1f}"
        min_score = min(a["work_satisfaction"], a["relationships"], a["health"])
        severity = "🔴 緊急" if min_score < config.CRITICAL_THRESHOLD else "🟡 注意"
        line = f"　{severity} {a['name']}（{a['department']}）- {scores}"
        if a.get("comment"):
            line += f"\n　　💬 {a['comment']}"
        alert_lines.append(line)

    body = f"""{hr_name} さん

{survey_title}の回答結果にアラート対象者が{len(alerts)}名います。
早期のフォローをお願いします。

━━ アラート対象者 ━━

{chr(10).join(alert_lines)}

━━━━━━━━━━━━━━

ダッシュボードで詳細を確認し、対応記録を残してください。
{config.BASE_URL}/admin/dashboard

──────────────
パルスサーベイシステム（自動通知）
"""
    return subject, body


# ─── メール送信 ──────────────────────────────────

def _send_email(to_address: str, subject: str, body: str, survey_id: int = None,
                employee_id: int = None, email_type: str = "invite") -> bool:
    """メールを送信（SMTP）"""
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{config.MAIL_FROM_NAME} <{config.MAIL_FROM_ADDRESS}>"
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if config.SMTP_USER and config.SMTP_PASSWORD:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            # SMTP未設定の場合はログ出力のみ（開発用）
            print(f"[メール送信（開発モード）] To: {to_address}")
            print(f"  件名: {subject}")
            print(f"  本文（先頭100文字）: {body[:100]}...")

        # 送信ログを記録
        if employee_id and survey_id:
            with db.get_db() as conn:
                conn.execute(
                    "INSERT INTO email_logs (employee_id, survey_id, email_type, status) VALUES (?, ?, ?, 'sent')",
                    (employee_id, survey_id, email_type),
                )
        return True

    except Exception as e:
        print(f"[メール送信エラー] {to_address}: {e}")
        if employee_id and survey_id:
            with db.get_db() as conn:
                conn.execute(
                    "INSERT INTO email_logs (employee_id, survey_id, email_type, status, error_message) VALUES (?, ?, ?, 'error', ?)",
                    (employee_id, survey_id, email_type, str(e)),
                )
        return False


def send_survey_invites(survey_id: int) -> dict:
    """
    サーベイの案内メールを全対象者に送信
    """
    survey = db.get_survey(survey_id)
    if not survey:
        raise ValueError("サーベイが見つかりません")

    unsent = db.get_unsent_tokens(survey_id)
    sent_count = 0
    error_count = 0

    for token_info in unsent:
        url = build_survey_url(token_info["token"])
        subject, body = _invite_template(
            employee_name=token_info["name"],
            survey_url=url,
            deadline=survey["deadline"],
            survey_title=survey["title"],
        )
        success = _send_email(
            to_address=token_info["email"],
            subject=subject,
            body=body,
            survey_id=survey_id,
            employee_id=token_info["employee_id"],
            email_type="invite",
        )
        if success:
            db.mark_token_sent(token_info["id"])
            sent_count += 1
        else:
            error_count += 1

    print(f"[案内メール送信完了] 成功: {sent_count}件, エラー: {error_count}件")
    return {"sent": sent_count, "errors": error_count}


def send_reminders(survey_id: int) -> dict:
    """
    未回答者にリマインドメールを送信
    """
    survey = db.get_survey(survey_id)
    if not survey:
        raise ValueError("サーベイが見つかりません")

    unreplied = db.get_unreplied_tokens(survey_id)
    sent_count = 0

    for token_info in unreplied:
        url = build_survey_url(token_info["token"])
        subject, body = _remind_template(
            employee_name=token_info["name"],
            survey_url=url,
            deadline=survey["deadline"],
            survey_title=survey["title"],
        )
        success = _send_email(
            to_address=token_info["email"],
            subject=subject,
            body=body,
            survey_id=survey_id,
            employee_id=token_info["employee_id"],
            email_type="remind",
        )
        if success:
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE survey_tokens SET reminded_at = datetime('now', 'localtime') WHERE id = ?",
                    (token_info["id"],),
                )
            sent_count += 1

    print(f"[リマインド送信完了] {sent_count}件送信（未回答: {len(unreplied)}名）")
    return {"sent": sent_count, "unreplied_total": len(unreplied)}


def send_alert_notification(survey_id: int, hr_email: str, hr_name: str = "人事担当者") -> bool:
    """
    人事担当者にアラート通知を送信
    """
    stats = db.get_survey_stats(survey_id)
    survey = db.get_survey(survey_id)

    if not stats["alerts"]:
        print("[アラート] アラート対象者はいません")
        return False

    subject, body = _alert_template(hr_name, stats["alerts"], survey["title"])
    return _send_email(hr_email, subject, body, survey_id, email_type="alert")
