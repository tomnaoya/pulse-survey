"""
パルスサーベイ CLIツール
コマンドラインからサーベイの作成・配信・集計を実行
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta

import database as db
import survey_manager as sm
import email_sender as mailer
import config


def cmd_init(args):
    """データベースを初期化"""
    db.init_db()
    print("✅ データベースを初期化しました")


def cmd_import_employees(args):
    """CSVから従業員を一括登録"""
    employees = []
    with open(args.file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            employees.append({
                "name": row["name"],
                "email": row["email"],
                "department": row["department"],
                "join_year": int(row["join_year"]) if row.get("join_year") else None,
            })

    count = db.import_employees_bulk(employees)
    print(f"✅ {count}名の従業員を登録しました")


def cmd_list_employees(args):
    """従業員一覧を表示"""
    employees = db.get_active_employees()
    if not employees:
        print("従業員が登録されていません")
        return

    print(f"\n{'ID':>4}  {'名前':<12}  {'部門':<16}  {'メール':<30}  {'入社年'}")
    print("─" * 80)
    for emp in employees:
        print(f"{emp['id']:>4}  {emp['name']:<12}  {emp['department']:<16}  {emp['email']:<30}  {emp.get('join_year', '-')}")
    print(f"\n合計: {len(employees)}名")


def cmd_create_survey(args):
    """新規サーベイを作成"""
    survey_id = db.create_survey(
        year_month=args.month,
        title=args.title or f"{args.month.replace('-', '年')}月度 パルスサーベイ",
        start_date=args.start,
        deadline=args.deadline,
        extra_question_title=args.extra_title,
        extra_question_desc=args.extra_desc,
    )
    print(f"✅ サーベイを作成しました (ID: {survey_id})")
    print(f"   期間: {args.start} 〜 {args.deadline}")


def cmd_prepare(args):
    """サーベイの配信準備（トークン生成）"""
    result = sm.prepare_survey(args.survey_id)
    print(f"\n✅ {result['total']}名分の回答URLを生成しました\n")
    print("サンプルURL（先頭5名）:")
    for t in result["tokens"][:5]:
        print(f"  {t['name']:<12} → {t['url']}")

    if result["total"] > 5:
        print(f"  ... 他 {result['total'] - 5}名")


def cmd_send(args):
    """案内メールを送信"""
    result = mailer.send_survey_invites(args.survey_id)
    print(f"\n✅ 案内メール送信完了")
    print(f"   送信成功: {result['sent']}件")
    if result["errors"] > 0:
        print(f"   送信エラー: {result['errors']}件")


def cmd_remind(args):
    """未回答者にリマインドメールを送信"""
    result = mailer.send_reminders(args.survey_id)
    print(f"\n✅ リマインド送信完了")
    print(f"   送信: {result['sent']}件")
    print(f"   未回答者合計: {result['unreplied_total']}名")


def cmd_progress(args):
    """進捗状況を表示"""
    progress = sm.get_survey_progress(args.survey_id)
    survey = db.get_survey(args.survey_id)

    print(f"\n📊 {survey['title']} - 進捗レポート")
    print("─" * 50)
    print(f"  回答率: {progress['response_rate']}% ({progress['total_responded']}/{progress['total_sent']}名)")
    print(f"  仕事満足度（平均）: {progress['avg_work']}")
    print(f"  人間関係（平均）:   {progress['avg_relationships']}")
    print(f"  健康（平均）:       {progress['avg_health']}")
    print(f"  アラート:           {progress['alert_count']}件")

    if progress["unreplied"]:
        print(f"\n📩 未回答者 ({len(progress['unreplied'])}名):")
        for u in progress["unreplied"]:
            print(f"  ・{u['name']} ({u['department']})")

    if progress["department_stats"]:
        print(f"\n🏢 部門別スコア:")
        for d in progress["department_stats"]:
            avg = round((d["avg_work"] + d["avg_rel"] + d["avg_health"]) / 3, 2)
            print(f"  {d['department']:<16} 総合: {avg}  (仕事:{d['avg_work']:.1f} 関係:{d['avg_rel']:.1f} 健康:{d['avg_health']:.1f})")


def cmd_alerts(args):
    """アラート対象者を表示"""
    stats = db.get_survey_stats(args.survey_id)

    if not stats["alerts"]:
        print("🎉 アラート対象者はいません")
        return

    print(f"\n⚠️ アラート対象者: {stats['alert_count']}名")
    print("─" * 60)
    for a in stats["alerts"]:
        min_score = min(a["work_satisfaction"], a["relationships"], a["health"])
        severity = "🔴 緊急" if min_score < config.CRITICAL_THRESHOLD else "🟡 注意"
        print(f"  {severity}  {a['name']} ({a['department']})")
        print(f"         仕事:{a['work_satisfaction']:.1f}  人間関係:{a['relationships']:.1f}  健康:{a['health']:.1f}")
        if a.get("comment"):
            print(f"         💬 {a['comment']}")
        print()


def cmd_close(args):
    """サーベイを締め切る"""
    db.close_survey(args.survey_id)
    print(f"✅ サーベイ (ID: {args.survey_id}) を締め切りました")


def cmd_export(args):
    """回答データをCSV出力"""
    responses = db.get_responses(args.survey_id)
    if not responses:
        print("回答データがありません")
        return

    output = args.output or f"survey_{args.survey_id}_responses.csv"
    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "department", "work_satisfaction", "relationships",
            "health", "extra_answer", "comment", "submitted_at",
        ])
        writer.writeheader()
        for r in responses:
            writer.writerow({
                "name": r["name"],
                "department": r["department"],
                "work_satisfaction": r["work_satisfaction"],
                "relationships": r["relationships"],
                "health": r["health"],
                "extra_answer": r.get("extra_answer", ""),
                "comment": r.get("comment", ""),
                "submitted_at": r["submitted_at"],
            })

    print(f"✅ {len(responses)}件の回答を {output} に出力しました")


def main():
    parser = argparse.ArgumentParser(
        description="パルスサーベイ管理ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 初期化
  python cli.py init

  # 従業員CSVインポート
  python cli.py import-employees employees.csv

  # サーベイ作成 → 配信準備 → 送信
  python cli.py create-survey --month 2026-03 --start 2026-03-01 --deadline 2026-03-14
  python cli.py prepare --survey-id 1
  python cli.py send --survey-id 1

  # 進捗確認・リマインド
  python cli.py progress --survey-id 1
  python cli.py remind --survey-id 1

  # アラート確認・CSV出力
  python cli.py alerts --survey-id 1
  python cli.py export --survey-id 1
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="データベースを初期化")

    # import-employees
    p = sub.add_parser("import-employees", help="CSVから従業員を一括登録")
    p.add_argument("file", help="CSVファイルパス（name, email, department, join_year）")

    # list-employees
    sub.add_parser("list-employees", help="従業員一覧を表示")

    # create-survey
    p = sub.add_parser("create-survey", help="新規サーベイを作成")
    p.add_argument("--month", required=True, help="対象月（例: 2026-03）")
    p.add_argument("--start", required=True, help="開始日（例: 2026-03-01）")
    p.add_argument("--deadline", required=True, help="締切日（例: 2026-03-14）")
    p.add_argument("--title", help="サーベイタイトル（省略時は自動生成）")
    p.add_argument("--extra-title", help="追加質問のタイトル")
    p.add_argument("--extra-desc", help="追加質問の説明")

    # prepare
    p = sub.add_parser("prepare", help="配信準備（トークン生成）")
    p.add_argument("--survey-id", type=int, required=True)

    # send
    p = sub.add_parser("send", help="案内メールを送信")
    p.add_argument("--survey-id", type=int, required=True)

    # remind
    p = sub.add_parser("remind", help="未回答者にリマインドを送信")
    p.add_argument("--survey-id", type=int, required=True)

    # progress
    p = sub.add_parser("progress", help="進捗状況を表示")
    p.add_argument("--survey-id", type=int, required=True)

    # alerts
    p = sub.add_parser("alerts", help="アラート対象者を表示")
    p.add_argument("--survey-id", type=int, required=True)

    # close
    p = sub.add_parser("close", help="サーベイを締め切る")
    p.add_argument("--survey-id", type=int, required=True)

    # export
    p = sub.add_parser("export", help="回答データをCSV出力")
    p.add_argument("--survey-id", type=int, required=True)
    p.add_argument("--output", help="出力ファイル名")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "init": cmd_init,
        "import-employees": cmd_import_employees,
        "list-employees": cmd_list_employees,
        "create-survey": cmd_create_survey,
        "prepare": cmd_prepare,
        "send": cmd_send,
        "remind": cmd_remind,
        "progress": cmd_progress,
        "alerts": cmd_alerts,
        "close": cmd_close,
        "export": cmd_export,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
