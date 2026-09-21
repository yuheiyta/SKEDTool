# JVN / VERA Schedule Tool

JVNのDRG、VERAのVEXを作成するFletアプリです。起動時に観測網を選択します。
JVNとVERAを統合した独立リポジトリです。

## 起動

```sh
conda activate schedule
python schedule_app.py
```

JVNだけを起動する場合は `python SKED_GUITool.py`、VERAだけの場合は
`python SKED_GUITool_vex.py` を使用できます。観測網の切替は再起動で行います。

Python 3.11.4 / Flet 0.7.4 と Python 3.11.8 / Flet 0.21.1 の既存環境で
自動テストを実行しています。requirements.txtはまだ厳密なロックではありません。
最新Fletへの無条件のアップグレードには対応していません。

## SKD変換

```sh
make -C drgconv
```

Cコンパイラとmakeが必要です。JVN画面の「Generate .skd from current schedule」で
編集中のスケジュールを変換し、結果をコピーできます。変換処理は一時ディレクトリを
処理ごとに分離します。元の変換器は日立・高萩の局情報を固定出力します。
macOSのバイナリは同梱せず、実行するOSでビルドしてください。
XML生成には同梱のmk_xml.pyを使用します。現在のXML画面はローカル向けです。

## テスト

```sh
python -m unittest discover -s tests -v
```

Flet画面はPageスタブで初期化・セッション分離を検証します。
実ブラウザの通し操作を検証するものではありません。

## 公開前の残作業

- Web版はコピペ入出力を採用。JVNの貼り付け入力とXML生成画面のWeb対応。
- IERSデータの更新状態・取得失敗の画面表示。
- 依存バージョン固定、Linuxビルドとブラウザでの検証。
- Render Free向けデプロイ設定。

この更新ではFly/Renderへのデプロイや契約変更は行っていません。
既存のFlyサービスと旧JVNリポジトリは維持します。
