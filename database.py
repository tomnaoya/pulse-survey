"""
データベース管理モジュール
従業員情報・サーベイ回答・トークン・対応記録を管理
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from config import DATABASE_PATH


@contextmanager
def get_db():
    """データベース接続のコンテキストマネージャ"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """テーブルの初期化"""
    with get_db() as conn:
        conn.executescript("""
            -- 従業員マスタ
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                join_year INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- サーベイ配信管理
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL UNIQUE,  -- "2026-02" 形式
                title TEXT NOT NULL,
                start_date TEXT NOT NULL,
                deadline TEXT NOT NULL,
                extra_question_title TEXT,         -- 追加質問（4問目）
                extra_question_description TEXT,
                status TEXT DEFAULT 'draft',       -- draft / active / closed
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- トークン管理（従業員 × サーベイごとに1トークン）
            CREATE TABLE IF NOT EXISTS survey_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                is_used INTEGER DEFAULT 0,
                sent_at TEXT,
                reminded_at TEXT,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (survey_id) REFERENCES surveys(id),
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                UNIQUE(survey_id, employee_id)
            );

            -- 回答データ
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                token_id INTEGER NOT NULL,
                work_satisfaction REAL NOT NULL CHECK(work_satisfaction BETWEEN 1 AND 5),
                relationships REAL NOT NULL CHECK(relationships BETWEEN 1 AND 5),
                health REAL NOT NULL CHECK(health BETWEEN 1 AND 5),
                extra_answer REAL,
                comment TEXT DEFAULT '',
                submitted_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (survey_id) REFERENCES surveys(id),
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (token_id) REFERENCES survey_tokens(id),
                UNIQUE(survey_id, employee_id)
            );

            -- 対応記録
            CREATE TABLE IF NOT EXISTS follow_up_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                survey_id INTEGER,
                author TEXT NOT NULL,
                note TEXT NOT NULL,
                action_type TEXT DEFAULT 'memo',  -- memo / meeting / call / email
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (survey_id) REFERENCES surveys(id)
            );

            -- メール送信ログ
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                survey_id INTEGER NOT NULL,
                email_type TEXT NOT NULL,  -- invite / remind / alert
                sent_at TEXT DEFAULT (datetime('now', 'localtime')),
                status TEXT DEFAULT 'sent',
                error_message TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (survey_id) REFERENCES surveys(id)
            );

            -- インデックス
            CREATE INDEX IF NOT EXISTS idx_tokens_token ON survey_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_tokens_survey ON survey_tokens(survey_id);
            CREATE INDEX IF NOT EXISTS idx_responses_survey ON responses(survey_id);
            CREATE INDEX IF NOT EXISTS idx_responses_employee ON responses(employee_id);
        """)
    print("[DB] テーブルの初期化が完了しました")


# ─── 従業員操作 ──────────────────────────────────

def add_employee(name: str, email: str, department: str, join_year: int = None) -> int:
    """従業員を追加"""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO employees (name, email, department, join_year) VALUES (?, ?, ?, ?)",
            (name, email, department, join_year),
        )
        return cursor.lastrowid


def import_employees_bulk(employees: list[dict]) -> int:
    """従業員を一括登録 [{"name": ..., "email": ..., "department": ..., "join_year": ...}, ...]"""
    count = 0
    with get_db() as conn:
        for emp in employees:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO employees (name, email, department, join_year) VALUES (?, ?, ?, ?)",
                    (emp["name"], emp["email"], emp["department"], emp.get("join_year")),
                )
                count += 1
            except sqlite3.IntegrityError:
                continue
    return count


def get_active_employees() -> list[dict]:
    """有効な従業員一覧を取得"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM employees WHERE is_active = 1 ORDER BY department, name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_employee_by_id(employee_id: int) -> dict | None:
    """従業員をIDで取得"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        return dict(row) if row else None


# ─── サーベイ操作 ─────────────────────────────────

def create_survey(year_month: str, title: str, start_date: str, deadline: str,
                  extra_question_title: str = None, extra_question_desc: str = None) -> int:
    """新規サーベイを作成"""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO surveys (year_month, title, start_date, deadline,
               extra_question_title, extra_question_description, status)
               VALUES (?, ?, ?, ?, ?, ?, 'draft')""",
            (year_month, title, start_date, deadline, extra_question_title, extra_question_desc),
        )
        return cursor.lastrowid


def get_survey(survey_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM surveys WHERE id = ?", (survey_id,)).fetchone()
        return dict(row) if row else None


def get_survey_by_month(year_month: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM surveys WHERE year_month = ?", (year_month,)).fetchone()
        return dict(row) if row else None


def activate_survey(survey_id: int):
    """サーベイを配信可能状態にする"""
    with get_db() as conn:
        conn.execute("UPDATE surveys SET status = 'active' WHERE id = ?", (survey_id,))


def close_survey(survey_id: int):
    """サーベイを締め切る"""
    with get_db() as conn:
        conn.execute("UPDATE surveys SET status = 'closed' WHERE id = ?", (survey_id,))


# ─── トークン操作 ─────────────────────────────────

def save_token(survey_id: int, employee_id: int, token: str, expires_at: str) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO survey_tokens
               (survey_id, employee_id, token, expires_at)
               VALUES (?, ?, ?, ?)""",
            (survey_id, employee_id, token, expires_at),
        )
        return cursor.lastrowid


def get_token_info(token: str) -> dict | None:
    """トークンから従業員・サーベイ情報を取得"""
    with get_db() as conn:
        row = conn.execute(
            """SELECT t.*, e.name as emp_name, e.email as emp_email, e.department,
                      s.year_month, s.title as survey_title, s.deadline, s.status as survey_status,
                      s.extra_question_title, s.extra_question_description
               FROM survey_tokens t
               JOIN employees e ON t.employee_id = e.id
               JOIN surveys s ON t.survey_id = s.id
               WHERE t.token = ?""",
            (token,),
        ).fetchone()
        return dict(row) if row else None


def mark_token_sent(token_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE survey_tokens SET sent_at = datetime('now', 'localtime') WHERE id = ?",
            (token_id,),
        )


def mark_token_used(token_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE survey_tokens SET is_used = 1 WHERE id = ?",
            (token_id,),
        )


def get_unsent_tokens(survey_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.*, e.name, e.email, e.department
               FROM survey_tokens t
               JOIN employees e ON t.employee_id = e.id
               WHERE t.survey_id = ? AND t.sent_at IS NULL""",
            (survey_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_unreplied_tokens(survey_id: int) -> list[dict]:
    """未回答者のトークン一覧"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.*, e.name, e.email, e.department
               FROM survey_tokens t
               JOIN employees e ON t.employee_id = e.id
               WHERE t.survey_id = ? AND t.is_used = 0 AND t.sent_at IS NOT NULL""",
            (survey_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ─── 回答操作 ──────────────────────────────────

def save_response(survey_id: int, employee_id: int, token_id: int,
                  work: float, relationships: float, health: float,
                  extra: float = None, comment: str = "") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO responses
               (survey_id, employee_id, token_id, work_satisfaction, relationships, health, extra_answer, comment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (survey_id, employee_id, token_id, work, relationships, health, extra, comment),
        )
        conn.execute(
            "UPDATE survey_tokens SET is_used = 1 WHERE id = ?",
            (token_id,),
        )
        return cursor.lastrowid


def get_responses(survey_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT r.*, e.name, e.department
               FROM responses r
               JOIN employees e ON r.employee_id = e.id
               WHERE r.survey_id = ?
               ORDER BY r.submitted_at DESC""",
            (survey_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_employee_history(employee_id: int) -> list[dict]:
    """従業員の回答履歴（全月分）"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT r.*, s.year_month, s.title as survey_title
               FROM responses r
               JOIN surveys s ON r.survey_id = s.id
               WHERE r.employee_id = ?
               ORDER BY s.year_month ASC""",
            (employee_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ─── 分析・集計 ──────────────────────────────────

def get_survey_stats(survey_id: int) -> dict:
    """サーベイの集計データを取得"""
    with get_db() as conn:
        # 全体統計
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM survey_tokens WHERE survey_id = ? AND sent_at IS NOT NULL",
            (survey_id,),
        ).fetchone()["cnt"]

        responded = conn.execute(
            "SELECT COUNT(*) as cnt FROM responses WHERE survey_id = ?",
            (survey_id,),
        ).fetchone()["cnt"]

        avg = conn.execute(
            """SELECT
                 AVG(work_satisfaction) as avg_work,
                 AVG(relationships) as avg_rel,
                 AVG(health) as avg_health
               FROM responses WHERE survey_id = ?""",
            (survey_id,),
        ).fetchone()

        # アラート対象
        from config import ALERT_THRESHOLD
        alerts = conn.execute(
            """SELECT r.*, e.name, e.department
               FROM responses r
               JOIN employees e ON r.employee_id = e.id
               WHERE r.survey_id = ?
                 AND (r.work_satisfaction < ? OR r.relationships < ? OR r.health < ?)""",
            (survey_id, ALERT_THRESHOLD, ALERT_THRESHOLD, ALERT_THRESHOLD),
        ).fetchall()

        # 部門別集計
        dept_stats = conn.execute(
            """SELECT e.department,
                 COUNT(*) as count,
                 AVG(r.work_satisfaction) as avg_work,
                 AVG(r.relationships) as avg_rel,
                 AVG(r.health) as avg_health
               FROM responses r
               JOIN employees e ON r.employee_id = e.id
               WHERE r.survey_id = ?
               GROUP BY e.department
               ORDER BY (AVG(r.work_satisfaction) + AVG(r.relationships) + AVG(r.health)) / 3 DESC""",
            (survey_id,),
        ).fetchall()

        return {
            "total_sent": total,
            "total_responded": responded,
            "response_rate": round(responded / total * 100, 1) if total > 0 else 0,
            "avg_work": round(avg["avg_work"], 2) if avg["avg_work"] else 0,
            "avg_relationships": round(avg["avg_rel"], 2) if avg["avg_rel"] else 0,
            "avg_health": round(avg["avg_health"], 2) if avg["avg_health"] else 0,
            "alert_count": len(alerts),
            "alerts": [dict(a) for a in alerts],
            "department_stats": [dict(d) for d in dept_stats],
        }


# ─── 対応記録 ──────────────────────────────────

def add_follow_up_note(employee_id: int, author: str, note: str,
                       survey_id: int = None, action_type: str = "memo") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO follow_up_notes (employee_id, survey_id, author, note, action_type)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, survey_id, author, note, action_type),
        )
        return cursor.lastrowid


def get_follow_up_notes(employee_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT n.*, s.year_month
               FROM follow_up_notes n
               LEFT JOIN surveys s ON n.survey_id = s.id
               WHERE n.employee_id = ?
               ORDER BY n.created_at DESC""",
            (employee_id,),
        ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("[DB] データベースの初期化が完了しました")
