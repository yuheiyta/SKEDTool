# Renderへのデプロイ

リポジトリ直下の `render.yaml`、`Dockerfile`、`.dockerignore`、`requirements.txt` を使用します。
別のdeploy用フォルダへのコピーは不要です。Python 3.11をDocker内で用意するため、手元のconda環境の変更も不要です。

## Blueprintで作成

1. 設定ファイルをGitHubの `yuheiyta/SKEDTool_JP` の `main` にpushします。
2. Render Dashboardで **New > Blueprint** を開き、GitHubの同リポジトリを接続します。
3. Branchを `main`、Blueprint Pathを `render.yaml` にします。
4. 作成対象が **skedtool / Web Service / Free の1サービスのみ** であることを確認します。
5. 公開する段階で **Deploy Blueprint** を実行します。初回の作成はこの操作でデプロイされます。
6. 発行された `https://….onrender.com` を開き、JVN / VERAの選択画面を確認します。

`autoDeployTrigger: "off"` は通常のソースpushによる自動デプロイを無効にします。
Blueprint自体の変更を自動適用する **Auto Sync** は別設定です。Blueprintの管理画面でも無効にすると、設定変更も手動で適用できます。
以後のコード更新はサービス画面の **Manual Deploy > Deploy latest commit** で反映します。

## Web Serviceとして手動作成する場合

Blueprintを使わず **New > Web Service** で同リポジトリを指定する場合の設定です。
Blueprint方式と両方で作成するとサービスが重複するため、どちらか一方を使います。

| 項目 | 値 |
| --- | --- |
| Branch | `main` |
| Language / Runtime | Docker |
| Root Directory | 空欄（リポジトリ直下） |
| Dockerfile Path | `./Dockerfile` |
| Docker Build Context | `.` |
| Docker Command | 空欄（DockerfileのCMDを使用） |
| Instance Type | Free |
| Health Check Path | `/` |
| Auto-Deploy | Off |
| Environment | `FLET_FORCE_WEB_SERVER=true`, `FLET_SESSION_TIMEOUT=600` |

Build Command、Start Command、秘密鍵、GitHubトークンの環境変数は不要です。
アプリは `0.0.0.0` とRenderが渡す `PORT` で待ち受けます。`PORT` の手動設定は不要です。

ブラウザのタブ用アイコンは `assets/favicon.png` です。既存の電波望遠鏡の画像を使用しています。
変更後に古いアイコンが残る場合は、ブラウザのサイトデータ／キャッシュを消すか、プライベートウィンドウで確認してください。

## 無料利用と保存

FreeのWeb Serviceを1つだけ使用し、DB・永続Diskは追加しません。
ただし、`plan: free` だけでアカウント全体の請求を完全に防ぐ設定にはなりません。
帯域・ビルド時間の枠を超えると、支払方法が登録されている場合は追加請求が発生し得ます。
費用を発生させたくない場合は支払方法を追加せず、Billingの使用量も確認してください。
支払方法がない場合、上限到達時はサービス停止や新規ビルド停止になります。

15分間受信通信がないと休止し、次のアクセスで起動に約1分かかります。
WebSocketの通信も休止判定に含まれるため、タブを開いたままでは休止しない場合があります。
編集状態と実行中に作成したファイルは再起動・休止で失われます。出力をコピーして手元で保存してください。

## 公開後の確認

- JVNとVERAを別タブで開き、一方の編集が他方に反映されないことを確認します。
- `Import from text` でDRG/VEXを貼り付け、出力画面からコピーします。
- Checkや仰角表示でIERSの取得結果とエラー表示を確認します。
- ブラウザのコピー許可が得られない場合は、出力テキストを手動選択してコピーします。

IERS-AはDockerビルド時に `prepare_iers_cache.py` で取得し、`/opt/sked-cache` に同梱します。
ビルド時は通信タイムアウト60秒、取得失敗・30日を超える古い予測データではビルドを失敗させます。
実行ユーザーが同じキャッシュを読み書きするため、起動時のコピーや有料の永続Diskは不要です。
休止・再起動ではビルド時のキャッシュに戻ります。必要に応じた自動更新は維持します。

同梱データを更新する際は **Manual Deploy > Clear build cache & deploy** を使います。
通常の再デプロイだけではDockerのビルドキャッシュが再利用され、データが更新されない場合があります。
半年ごとの更新でも自動取得は働きますが、予測値の鮮度判定（30日）を超えた後は利用時のDLが再発し得ます。
DL待ちを抑えるなら、余裕を見て2〜3週間ごとの更新が目安です。30日はDL日ではなく、表の予測開始日から判定されます。
ビルド時間も無料利用枠に含まれるため、使用頻度に合わせて更新してください。
第三者作成の `drgconv` と `mk_xml.py` はDockerに含まれず、SKD/XML生成ボタンは無効です。

## ローカルでのコンテナ確認

Dockerが起動した環境でリポジトリ直下から実行します。

```sh
docker build -t skedtool .
docker run --rm -p 8000:8000 -e PORT=8000 skedtool
```

`http://localhost:8000` で確認します。Linuxコンテナのビルドと実ブラウザの通し確認は、別途実施が必要です。
メモリ不足で終了する場合はLogsを確認し、有料プランへの変更前に原因を調べてください。

## 公式資料

2026-09-21確認。サービス仕様は変更される場合があります。

- [Blueprintの作成](https://render.com/docs/infrastructure-as-code)
- [Blueprint設定項目](https://render.com/docs/blueprint-spec)
- [無料枠・休止・超過時の扱い](https://render.com/docs/free)
