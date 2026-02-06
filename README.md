# パルスサーベイシステム（Geppo型）

従業員のコンディションを毎月3問で把握するパルスサーベイシステムのバックエンド実装です。

## システム構成

```
geppo/
├── config.py            # 設定ファイル（DB・メール・閾値）
├── database.py          # データベース操作（SQLite）
├── survey_manager.py    # トークン生成・回答管理
├── email_sender.py      # メール配信（案内・リマインド・アラート）
├── app.py               # Flask Web API
├── cli.py               # コマンドライン管理ツール
├── demo.py              # デモスクリプト
└── sample_employees.csv # サンプル従業員データ
```

## セットアップ

```bash
pip install flask
python database.py    # DB初期化
```

## 運用フロー

### 1. 従業員の登録

```bash
# CSVからインポート（name, email, department, join_year）
python cli.py import-employees sample_employees.csv

# 一覧確認
python cli.py list-employees
```

### 2. サーベイの作成

```bash
python cli.py create-survey \
  --month 2026-03 \
  --start 2026-03-01 \
  --deadline 2026-03-14
```

追加質問（4問目）を設定する場合:
```bash
python cli.py create-survey \
  --month 2026-03 \
  --start 2026-03-01 \
  --deadline 2026-03-14 \
  --extra-title "リモートワーク" \
  --extra-desc "リモートワーク環境の満足度はいかがですか？"
```

### 3. 配信準備（トークン生成）

```bash
python cli.py prepare --survey-id 1
```

各従業員にユニークなURLが生成されます:
```
田中太郎 → http://localhost:5000/survey/aBcDeFgH1234...
佐藤花子 → http://localhost:5000/survey/xYzAbCdE5678...
```

### 4. 案内メール送信

```bash
python cli.py send --survey-id 1
```

### 5. 進捗確認

```bash
python cli.py progress --survey-id 1
```

### 6. リマインド送信

```bash
python cli.py remind --survey-id 1
```

### 7. アラート確認

```bash
python cli.py alerts --survey-id 1
```

### 8. 回答データ出力

```bash
python cli.py export --survey-id 1 --output results.csv
```

### 9. サーベイ締切

```bash
python cli.py close --survey-id 1
```

## Web API

```bash
python app.py  # サーバー起動（http://localhost:5000）
```

### 従業員向けエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/survey/<token>` | サーベイ回答ページ |
| GET | `/api/survey/validate/<token>` | トークン検証 |
| POST | `/api/survey/submit` | 回答送信 |

### 管理者向けエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/admin/surveys` | サーベイ一覧 |
| POST | `/api/admin/surveys` | サーベイ作成 |
| POST | `/api/admin/surveys/<id>/prepare` | 配信準備 |
| POST | `/api/admin/surveys/<id>/send` | 案内メール送信 |
| POST | `/api/admin/surveys/<id>/remind` | リマインド送信 |
| GET | `/api/admin/surveys/<id>/stats` | 集計結果 |
| GET | `/api/admin/surveys/<id>/progress` | 進捗状況 |
| POST | `/api/admin/surveys/<id>/close` | 締切 |
| GET | `/api/admin/employees` | 従業員一覧 |
| POST | `/api/admin/employees/import` | 従業員一括登録 |
| GET | `/api/admin/employees/<id>` | 従業員詳細 |
| POST | `/api/admin/employees/<id>/notes` | 対応記録追加 |

## メール設定

環境変数で設定:

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export MAIL_FROM_NAME=人事部
export MAIL_FROM_ADDRESS=hr@yourcompany.com
export SURVEY_BASE_URL=https://survey.yourcompany.com
export SURVEY_SECRET_KEY=your-random-secret-key
```

SMTP未設定時はコンソールにログ出力されます（開発モード）。

## デモ実行

```bash
python demo.py
```

初期化 → 従業員登録 → サーベイ作成 → トークン生成 → メール送信 →
回答シミュレート → 集計 → リマインド → 対応記録 の一連の流れを実演します。
