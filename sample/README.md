# TimeTree Scraper (separate project)

## 概要
- APIから返ってきた全カレンダーを対象に予定を取得
- 指定開始日から31日間（開始日 + 30日）を取得
- キーワードを含む予定のみ抽出可能
- SQLiteへ保存し、CSV出力可能
- Tkinter UI付き

## セットアップ
```bash
pip install selenium requests
export TIMETREE_EMAIL='your-email'
export TIMETREE_PASSWORD='your-password'
```

## CLI
### 取得してDB保存
```bash
python timetree_project/run_scrape.py --start-date 2026-03-16 --keyword 会議
```

### CSV出力
```bash
python timetree_project/export_csv.py --start-date 2026-03-16 --output timetree_project/events.csv
```

## UI
```bash
python timetree_project/ui.py
```
