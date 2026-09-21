# JVN / VERA Schedule Tool

起動時にJVN（DRG）／VERA（VEX）を選ぶスケジュール編集アプリです。
全スキャンで局構成は共通、VERAはVm・Vr・Vo・Vsの4局を前提にしています。

## 起動

既存環境はそのまま利用できます。

```sh
conda activate schedule
python schedule_app.py
```

新規インストールの検証用構成はPython 3.11 / Flet 0.21.2です。
既存conda環境を上書きせず、別のvenvで作成してください。

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python schedule_app.py
```

`requirements.in` は主要依存、`requirements.txt` は検証用macOS環境の解決済みバージョンです。
Linux固有の追加依存はDockerビルド時にも確認してください。
Flet 0.21.1はPyPIから取得できなかったため、同系列の0.21.2を選んでいます。
Flet 1.xへの移行はしていません。PythonのDockerタグは3.11系列を追従し、digest固定ではありません。

JVNだけなら `python SKED_GUITool.py`、VERAだけなら `python SKED_GUITool_vex.py` でも起動できます。
観測網を変える場合はアプリを再起動（Webでは別タブを開く）してください。

## Web版・ローカル版の入出力

Web版は `Import from text` にDRG/VEXを貼り付け、`Copy Clipboard` で出力画面を開きます。
出力画面のCopyボタン、またはテキストの手動選択でコピーして、手元で保存してください。
ファイルアップロードや共有ダウンロードURLは作りません。
ローカル版では従来のImport/Exportによるファイル操作も使えます。

読み込みは成功時のみ反映します。不正な貼り付けで直前の編集内容は上書きしません。
ブラウザを閉じたりサーバーが停止すると編集状態は失われます。必要な内容は手元に保存してください。

ローカルでWeb動作を試す場合:

```sh
FLET_FORCE_WEB_SERVER=true PORT=8000 python schedule_app.py
```

ブラウザで `http://localhost:8000` を開きます。

## IERSデータ

Check時にIERSデータを確認し、収録範囲・出典・観測値/予測値の区別を表示します。
仰角等の計算前にも確認します。範囲外、古い予測値の更新失敗などはエラーとし、OK扱いしません。
自動更新は有効、取得タイムアウト10秒、予測データの更新判定は30日です。
キャッシュの永続Volumeは不要です。再起動後に必要な場合だけ再取得します。

`astropy-iers-data` のバージョンもrequirements.txtに記録しています。
将来の更新時は、一時環境で同パッケージを更新し、テスト後にrequirements.txtを再生成します。
有効期限を無効化する `auto_max_age=None` は使いません。

## 任意の外部変換ツール（再配布しません）

`drgconv` と `mk_xml.py` は第三者作成で、再配布許可を未確認のため同梱しません。
本リポジトリのLICENSEは、これらの外部ツールの再配布許可を意味しません。
Dockerのコピー対象からも除外しています。

利用許可のあるツールをローカルで用意した場合のみ、次の環境変数で指定できます。

```sh
export SKED_DRGCONV=/absolute/path/to/drgconv2020
export SKED_XML_SCRIPT=/absolute/path/to/mk_xml.py
python schedule_app.py
```

未設定時はリポジトリ直下の `drgconv/drgconv2020`、`mk_xml.py` を探します。
存在しない場合は生成ボタンを無効化します。DRG/VEX編集は引き続き利用できます。
外部ツールは実行するOSに対応したものを用意してください。
SKD/XML生成は編集中のDRGを処理専用の一時ディレクトリに書き、生成物をコピー用画面で返します。
実行は30秒で打ち切り、一時ファイルは削除します。

## テスト

```sh
python -m unittest discover -s tests -v
```

球面中点、読み込みの失敗時保持、利用者間の分離、Webコピペ、局構成、
IERSの予測値/範囲外/取得失敗、外部ツールの分離、カタログ検索を検証します。
外部変換ツールそのものはテストに不要です。テスト用の小さい独自スクリプトを使います。
Flet画面テストにはPageスタブを使用するため、実ブラウザの通し確認は別途必要です。

## Render向け設定（未デプロイ）

`Dockerfile`、`.dockerignore`、`render.yaml` を用意しています。
RenderのFreeを指定し、自動デプロイを無効にしています。Volume・DBは作成しません。
ポートはRenderの `PORT` を使用します。
外部変換ツール、ローカルの認証情報、Git履歴はイメージに含めません。

公開前にLinuxでのDockerビルドと、無料インスタンスでのメモリ・速度を確認してください。
実行例: `docker build -t skedtool .`、`docker run --rm -p 8000:8000 skedtool`。
この作業でFly/Renderへのデプロイや契約変更は行っていません。
