# HTML Monitor

指定したURLのページ本文テキストを定期的に取得し、前回から変化があれば Discord に差分を通知します。常時起動している Windows PC で常駐させて動かします。

## 構成

```
monitor.py         取得・比較・通知の本体(--loop で常駐)
install-task.ps1   Windows の起動時に自動で常駐させるタスクを登録
urls.yml           監視対象の一覧
.env.example       設定ファイルのひな形(.env にコピーして使う)
requirements.txt
snapshots/         前回のテキスト(自動生成・git管理外)
logs/              実行ログ(自動生成・git管理外)
```

## セットアップ(Windows)

事前に [Python](https://www.python.org/downloads/windows/) と [Git](https://git-scm.com/download/win) をインストールしておきます(Python のインストーラでは「Add python.exe to PATH」にチェック)。

1. **Discord Webhook を作る**
   通知したいチャンネルの「チャンネルの編集 → 連携サービス → ウェブフック → 新しいウェブフック」で作成し、URLをコピー。

2. **リポジトリを取得して環境を作る**(PowerShell)
   ```powershell
   git clone https://github.com/isct-meken-dev/HTMLmonitor.git C:\HTMLmonitor
   cd C:\HTMLmonitor
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

3. **Webhook URL を設定**
   ```powershell
   copy .env.example .env
   notepad .env    # DISCORD_WEBHOOK_URL を書き換えて保存
   ```

4. **手動で1回実行して動作確認**
   ```powershell
   .venv\Scripts\python monitor.py
   ```
   初回は `[init]` と出てスナップショットを保存するだけで、通知は来ません。

5. **常駐タスクを登録**
   PowerShell を「管理者として実行」で開き:
   ```powershell
   cd C:\HTMLmonitor
   powershell -ExecutionPolicy Bypass -File .\install-task.ps1
   ```
   以後、PC起動時に自動で `monitor.py --loop` が立ち上がり、10分ごとにチェックします。ログオンしていなくても動き、異常終了しても1分後に自動で再起動します。

## 通知の例

```
変更を検知: お知らせページ
https://example.org/news
追加 2 行 / 削除 1 行
@@ -3,3 +3,4 @@
 お知らせ
-2026年10月の営業日について
+2026年11月の営業日について
+年末年始休業のご案内
```

## 運用

- **動作確認**: `Get-ScheduledTask HTMLMonitor`(State が Running なら稼働中)、ログは `Get-Content logs\monitor.log -Tail 20 -Wait`。
- **監視対象の変更**: `urls.yml` を書き換えるだけで、次回のチェックから反映されます(再起動不要)。
- **コード・`.env` の変更**: 反映には再起動が必要です。
  ```powershell
  git pull
  Stop-ScheduledTask HTMLMonitor; Start-ScheduledTask HTMLMonitor
  ```
- **チェック間隔**: `.env` の `INTERVAL_MINUTES`(分)。相手サイトへの負荷を考えて10分以上を推奨。
- **誤検知が多いとき**: 毎回変わる日時・アクセス数などが原因です。`urls.yml` の `ignore_patterns` に正規表現を足すと、その部分を無視できます。
- **取得エラーも知りたいとき**: `.env` の `NOTIFY_ERRORS` を `true` に。
- **ログ**: `logs\monitor.log` は 5MB を超えると自動でローテーションされます(最大3世代)。
- **止める / 削除する**: `Stop-ScheduledTask HTMLMonitor` / `Unregister-ScheduledTask HTMLMonitor`。

## 注意

- PCが停止・スリープしている間はチェックされません。電源設定でスリープを「なし」にしてください。
- JavaScript で後から描画されるページ(SPA など)は、取得したHTMLに本文が含まれないため検知できません。その場合は Playwright を使う版に差し替えが必要です。
- 監視先サイトの利用規約やrobots.txtを確認し、過度な頻度でアクセスしないでください。
