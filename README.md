# HTML Monitor

指定したURLのページ本文テキストを定期的に取得し、前回から変化があれば Discord に差分を通知します。GitHub Actions で動くのでサーバーは不要です。

## 構成

```
.github/workflows/monitor.yml  定期実行(30分ごと)
monitor.py                     取得・比較・通知の本体
urls.yml                       監視対象の一覧
requirements.txt
snapshots/                     前回のテキスト(自動生成・自動コミット)
```

## セットアップ

0. **ワークフローファイルを所定の場所へ移動**(初回のみ)
   ```bash
   cd ~/html-monitor
   mkdir -p .github/workflows && mv workflow-monitor.yml .github/workflows/monitor.yml
   ```

1. **Discord Webhook を作る**
   通知したいチャンネルの「チャンネルの編集 → 連携サービス → ウェブフック → 新しいウェブフック」で作成し、URLをコピー。

2. **GitHub にリポジトリを作り、このフォルダの中身を push**
   監視対象のURLを公開したくない場合はプライベートリポジトリにしてください(プライベートでも無料枠内で十分動きます)。

3. **Webhook URL を Secret に登録**
   リポジトリの Settings → Secrets and variables → Actions → New repository secret
   - Name: `DISCORD_WEBHOOK_URL`
   - Secret: コピーしたWebhook URL

4. **監視対象を設定**
   `urls.yml` の `url` を監視したいページに書き換えて push。

5. **初回実行**
   Actions タブ → HTML Monitor → Run workflow。初回はスナップショットを保存するだけで通知は来ません。次回以降、変化があると Discord に届きます。

## 通知の例

```
🔔 変更を検知: お知らせページ
https://example.org/news
追加 2 行 / 削除 1 行
@@ -3,3 +3,4 @@
 お知らせ
-2026年10月の営業日について
+2026年11月の営業日について
+年末年始休業のご案内
```

## 調整ポイント

- **チェック間隔**: `monitor.yml` の `cron`。`*/15 * * * *` で15分ごと、`0 * * * *` で1時間ごと。GitHub Actions の最短は5分ですが、相手サイトへの負荷を考えて15分以上がおすすめです。
- **誤検知が多いとき**: 毎回変わる日時・アクセス数・ランダムなおすすめ記事などが原因です。`urls.yml` の `ignore_patterns` に正規表現を足すと、その部分を無視できます。
- **取得エラーも知りたいとき**: `monitor.yml` の `NOTIFY_ERRORS` を `"true"` に。
- **ローカルで試す**:
  ```bash
  pip install -r requirements.txt
  DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." python monitor.py
  ```
  Webhook未設定なら通知内容をコンソールに出すだけになります。

## 注意

- JavaScript で後から描画されるページ(SPA など)は、取得したHTMLに本文が含まれないため検知できません。その場合は Playwright を使う版に差し替えが必要です。
- 60日間リポジトリに動きがないと GitHub がスケジュール実行を自動停止します。本システムはスナップショットをコミットするので、ページに変化がある限り止まりませんが、変化が全くないページだけを監視していると止まることがあります(停止前にメールで通知が来ます)。
- 監視先サイトの利用規約やrobots.txtを確認し、過度な頻度でアクセスしないでください。
