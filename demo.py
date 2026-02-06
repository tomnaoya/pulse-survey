"""
デモスクリプト - サーベイ配信〜回答〜集計の一連の流れを実演
"""
import random
import database as db
import survey_manager as sm
import email_sender as mailer


def run_demo():
    print("=" * 60)
    print("  パルスサーベイシステム - デモ実行")
    print("=" * 60)

    # ── Step 1: 初期化 ─────────────────────────
    print("\n📦 Step 1: データベース初期化")
    db.init_db()

    # ── Step 2: 従業員登録 ──────────────────────
    print("\n👥 Step 2: 従業員をCSVからインポート")
    import csv
    employees = []
    with open("sample_employees.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            employees.append({
                "name": row["name"],
                "email": row["email"],
                "department": row["department"],
                "join_year": int(row["join_year"]) if row.get("join_year") else None,
            })
    count = db.import_employees_bulk(employees)
    print(f"   → {count}名を登録しました")

    # ── Step 3: サーベイ作成 ────────────────────
    print("\n📝 Step 3: 2026年3月度サーベイを作成")
    survey_id = db.create_survey(
        year_month="2026-03",
        title="2026年3月度 パルスサーベイ",
        start_date="2026-03-01",
        deadline="2026-03-14",
    )
    print(f"   → サーベイID: {survey_id}")

    # ── Step 4: 配信準備（トークン生成） ───────
    print("\n🔑 Step 4: 全従業員の回答URLを生成")
    result = sm.prepare_survey(survey_id)
    print(f"   → {result['total']}名分のURLを生成")
    print("\n   サンプルURL:")
    for t in result["tokens"][:3]:
        print(f"   {t['name']:<12} → {t['url']}")
    print(f"   ... 他 {result['total'] - 3}名")

    # ── Step 5: 案内メール送信 ──────────────────
    print("\n📧 Step 5: 案内メールを送信")
    send_result = mailer.send_survey_invites(survey_id)
    print(f"   → {send_result['sent']}件送信完了")

    # ── Step 6: 回答をシミュレート ──────────────
    print("\n✍️  Step 6: 回答をシミュレート（ランダム）")
    tokens = result["tokens"]
    responded = 0
    for t in tokens:
        # 90%の確率で回答
        if random.random() < 0.90:
            work = round(random.uniform(1.0, 5.0), 1)
            rel = round(random.uniform(1.0, 5.0), 1)
            health = round(random.uniform(1.5, 5.0), 1)
            comments = [
                "", "", "", "",  # 多くの人はコメントなし
                "業務量が多く、キャパオーバー気味です",
                "チーム内のコミュニケーションに課題を感じます",
                "新しいスキルの習得を進めています",
                "ワークライフバランスは概ね良好です",
                "もっとチャレンジングな仕事がしたい",
                "リモートで孤立感を感じることがあります",
            ]
            comment = random.choice(comments)
            try:
                sm.submit_response(
                    token=t["token"],
                    work=work, relationships=rel, health=health,
                    comment=comment,
                )
                responded += 1
            except ValueError:
                pass

    print(f"   → {responded}/{len(tokens)}名が回答（回答率: {responded/len(tokens)*100:.0f}%）")

    # ── Step 7: 進捗確認 ───────────────────────
    print("\n📊 Step 7: 集計結果")
    stats = db.get_survey_stats(survey_id)
    print(f"   回答率:        {stats['response_rate']}%")
    print(f"   仕事満足度:    {stats['avg_work']}")
    print(f"   人間関係:      {stats['avg_relationships']}")
    print(f"   健康:          {stats['avg_health']}")
    print(f"   アラート:      {stats['alert_count']}件")

    # 部門別
    print("\n   🏢 部門別スコア:")
    for d in stats["department_stats"]:
        avg = round((d["avg_work"] + d["avg_rel"] + d["avg_health"]) / 3, 2)
        print(f"      {d['department']:<18} 総合: {avg}")

    # アラート
    if stats["alerts"]:
        print(f"\n   ⚠️ アラート対象者:")
        for a in stats["alerts"][:5]:
            min_s = min(a["work_satisfaction"], a["relationships"], a["health"])
            level = "🔴" if min_s < 1.5 else "🟡"
            print(f"      {level} {a['name']}（{a['department']}） 仕事:{a['work_satisfaction']:.1f} 関係:{a['relationships']:.1f} 健康:{a['health']:.1f}")
            if a.get("comment"):
                print(f"         💬 {a['comment']}")

    # ── Step 8: 未回答者にリマインド ────────────
    unreplied = db.get_unreplied_tokens(survey_id)
    if unreplied:
        print(f"\n📩 Step 8: 未回答者 {len(unreplied)}名にリマインド送信")
        remind_result = mailer.send_reminders(survey_id)
        print(f"   → {remind_result['sent']}件送信")
    else:
        print("\n📩 Step 8: 全員回答済みのためリマインド不要")

    # ── Step 9: 対応記録を追加 ──────────────────
    if stats["alerts"]:
        alert = stats["alerts"][0]
        print(f"\n📋 Step 9: 対応記録を追加 ({alert['name']})")
        db.add_follow_up_note(
            employee_id=alert["employee_id"],
            author="人事: デモ担当",
            note="1on1を実施。業務量の見直しについて上長と相談予定。",
            survey_id=survey_id,
            action_type="meeting",
        )
        print("   → 面談記録を登録しました")

    # ── 完了 ───────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ デモ完了！")
    print()
    print("  次のステップ:")
    print("  1. python app.py でWebサーバーを起動")
    print("  2. ブラウザで http://localhost:5000/health を確認")
    print("  3. APIエンドポイントで操作")
    print()
    print("  CLIの使い方:")
    print("  python cli.py --help")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
