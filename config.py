"""
パルスサーベイシステム 設定ファイル
"""
import os

# ─── 基本設定 ──────────────────────────────────
APP_NAME = "パルスサーベイシステム"
SECRET_KEY = os.environ.get("SURVEY_SECRET_KEY", "your-secret-key-change-in-production")
BASE_URL = os.environ.get("SURVEY_BASE_URL", "http://localhost:5000")

# ─── データベース ──────────────────────────────
DATABASE_PATH = os.environ.get("SURVEY_DB_PATH", "survey.db")

# ─── メール設定 ─────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "人事部")
MAIL_FROM_ADDRESS = os.environ.get("MAIL_FROM_ADDRESS", "hr@example.com")

# ─── サーベイ設定 ─────────────────────────────────
# トークンの有効期限（日数）
TOKEN_EXPIRY_DAYS = 14

# サーベイの質問（固定3問 + 追加質問対応）
SURVEY_QUESTIONS = [
    {
        "key": "work_satisfaction",
        "title": "仕事満足度",
        "description": "現在の仕事内容や業務量に対する満足度はいかがですか？",
    },
    {
        "key": "relationships",
        "title": "人間関係",
        "description": "上司・同僚との関係性やチームの雰囲気はいかがですか？",
    },
    {
        "key": "health",
        "title": "健康",
        "description": "心身の健康状態はいかがですか？（体調・睡眠・ストレスなど）",
    },
]

# スコアの閾値
ALERT_THRESHOLD = 2.5  # これ以下でアラート
CRITICAL_THRESHOLD = 1.5  # これ以下で緊急アラート

# リマインド設定
REMIND_DAYS_BEFORE_DEADLINE = [3, 1]  # 締切の何日前にリマインドするか
