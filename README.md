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

## 外部の変換ツール

`drgconv` と `mk_xml.py` は第三者が作成したツールです。
再配布許可を未確認のため、このリポジトリには同梱しません。
本リポジトリのLICENSEは、これらの外部ツールの再配布許可を意味しません。

DRG/VEXの編集機能はこれらのツールがなくても利用できます。
SKD/XML生成は、利用許可のあるツールを別途ローカルに用意した場合のみ使用してください。
これらのファイルはGitの追跡対象から除外しています。

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
