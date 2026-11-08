# business-english-commute

通勤などのスキマ時間に、iPhone でビジネス英語の基礎（語彙・音声変化・定型表現・実務文法・会話の聞き取り）を学ぶための Streamlit アプリです。対象は中上級（TOEIC 750 以上）、利用者は本人 1 名を想定しています。

- 要件定義: [docs/requirements.md](docs/requirements.md)
- 公開 URL: https://business-english-commute.streamlit.app/ （パスコードを入力するまでは、学習履歴を保存しないお試しモードで動きます）

## できること

| タブ | 内容 |
|------|------|
| 🏠 今日 | 今日の復習件数・連続学習日数・今日の学習時間と、5 分クイズ／書き取り／聞き流しへのショートカット |
| 📝 クイズ | 3／5／10 分の時間制。英→日・日→英・音声→意味・音声変化の聞き取り・自然な表現の選択を 4 択などで出題 |
| ✍️ 書き取り | 英文を聞いてタイプし、単語ごとに色分けで答え合わせ（大文字小文字・句読点・縮約形・数字の書き方の違いは誤りにしない） |
| 🎧 聞き流し | 英語のみを、繰り返し回数・ポーズ・速さを選んで連続再生。復習期限の来た英文だけを流す「今日の復習」もある |
| 🗣 発音 | 言い回しと発音を身につける。英文・意味・解説を見ながらお手本を聞いて読み上げ、Safari 標準の音声認識で一致率と言えなかった語を表示 |
| 🔁 シャドーイング | 聞き取りの確認。日本語は出さず、英語の音声だけを聞いて聞こえたとおりに言い、正解／惜しい／不正解を判定。英文は話し終えてから表示 |
| 📚 辞書 | 収録項目を英語・日本語で検索し、音声付きで閲覧。内容が怪しい項目に「要確認」の印を付けられる |
| 📊 記録 | 領域別の進み具合と正答率、直近 14 日の学習時間、苦手な項目 |

クイズと書き取りは、間違えた問題ほど早く、正解した問題ほど間隔をあけて出し直します（SM-2 を簡略化した間隔反復）。

## 前提条件

- Python 3.11
- 利用端末は iPhone の Safari（ホーム画面に追加して使う場合を含む）。ほかのブラウザでも動く見込みですが、動作確認の対象外です
- オンライン前提です（音声の読み上げと音声認識は端末とブラウザの機能を使います）

## ローカルで動かす

Windows（PowerShell）:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS / Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

期待される結果: ブラウザで `http://localhost:8501` が開き、「🏠 今日」の画面が表示されます。Secrets を何も設定していない場合は「🧪 お試しモード（学習履歴は保存されません）」と表示され、そのまま全機能を試せます。

ローカルで学習履歴を残したい場合は、`.streamlit/secrets.toml` に次の 1 行を書きます（このファイルは `.gitignore` 済みです）。

```toml
PROGRESS_FILE = "progress.local.json"
```

## 学習履歴を GitHub Gist に保存する

公開 URL は誰でも開けるため、**パスコードを入力するまで Gist には接続しません**（入力前はお試しモード）。

1. [gist.github.com](https://gist.github.com) で **Secret gist** を作成します。ファイル名は `progress.json`、内容は `{}` だけにします
   - Secret gist は一覧や検索には出ませんが、URL を知っている人は閲覧できます。保存されるのは問題の ID・復習日・正答数などの学習記録だけで、個人情報は含みません
2. 作成した Gist の URL（`https://gist.github.com/<ユーザー名>/<GIST_ID>`）の末尾の英数字を控えます
3. GitHub の Settings → Developer settings → Personal access tokens でトークンを作成します
   - fine-grained トークンの場合: Account permissions の **Gists** を Read and write にします（ほかの権限は不要です）
   - classic トークンの場合: スコープは `gist` のみにします
4. `.streamlit/secrets.toml.example` を `.streamlit/secrets.toml` にコピーし、値を書き換えます

```toml
APP_PASSCODE = "自分で決めたパスコード"
GIST_ID = "控えた GIST_ID"
GITHUB_TOKEN = "作成したトークン"
```

期待される結果: アプリを開くと「🔒 パスコードを入力すると学習履歴が保存されます」が表示され、パスコードを入力すると「☁️ 学習履歴は GitHub Gist に保存されます」に変わります。

- `secrets.toml` とトークンは**絶対にコミットしないでください**（`.gitignore` で除外済みです）
- 保存は「5 問回答するごと」「セッション終了時」「タブを切り替えたとき」にまとめて行います。アプリを閉じると、最大で直近 4 問分の結果が失われることがあります
- `GIST_ID` と `GITHUB_TOKEN` だけを設定して `APP_PASSCODE` を設定しなかった場合は、誰でも履歴を書き換えられる状態を避けるため、保存を止めてエラーを表示します
- 読み込みに失敗した場合は、Gist の履歴を空のデータで上書きしないよう、その間の学習は保存しません（画面の「学習履歴を読み込み直す」で再試行できます）

## Streamlit Community Cloud にデプロイする

1. このリポジトリを GitHub に公開リポジトリとして push します
2. [share.streamlit.io](https://share.streamlit.io) で Create app を選び、リポジトリ・ブランチ `main`・ファイル `app.py` を指定します
3. Advanced settings で Python のバージョンを 3.11 にし、Secrets 欄に上の `secrets.toml` と同じ内容を貼り付けます
4. Deploy を押します

期待される結果: 数分で公開 URL が発行され、iPhone の Safari から開けます。しばらく使わないとアプリがスリープし、次に開いたときの起動に数十秒かかることがあります。

## iPhone での使い方のヒント

- Safari の共有メニューから「ホーム画面に追加」すると、アプリのように起動できます
- `https://<公開URL>/?key=<パスコード>` の形で開くと、パスコードの入力を省けます。ただしパスコードが URL と閲覧履歴に残るため、この URL は人に共有しないでください
- 音が出ない場合は、音量と消音モード（サイレントスイッチ）の設定を確認してください
- 発音・シャドーイングのタブで「マイクの使用が許可されていません」と出る場合は、設定アプリの Safari（iOS 18 以降は「アプリ」の中）でマイクの設定を確認してください。「音声認識が許可されていません」と出る場合は、設定アプリ → 一般 → キーボード の「音声入力」を確認してください
- 書き取りの入力欄では、自動修正・自動大文字化・スペルチェックを止める設定にしています。それでも修正が入る場合は、1 文字程度の違いなら「惜しい」と判定します

## 制限事項

- **画面をロックすると読み上げが止まります。** 音声は iPhone 内蔵の読み上げ（Web Speech API）を使っているためです。聞き流しでは「再生中は画面を消さない」をオンにしてください。画面ロック中も流せる音声ファイル方式は未決事項（要件定義の Q-03）です
- 内蔵の読み上げは、人が話す自然な音声に比べて音声変化（リエゾンなど）が弱めに聞こえることがあります。各規則の解説とあわせて使ってください
- 発音・シャドーイングの判定に使うブラウザの音声認識は、音声を Apple などのブラウザ提供元のサーバーに送って処理する場合があります。読み上げるのはアプリの例文のみで、個人情報は含みません
- 判定は音声認識の書き起こしと英文を比べて行うため、正しく言えていても、同じ発音の別の語（their / there など）に書き起こされて不正解になることがあります。発音・シャドーイングの判定結果は、学習履歴（復習の予定）には記録しません
- 学習コンテンツは AI が作成したものです。誤りに気づいたら、辞書などの「🏳️ 内容が怪しい（要確認）」で印を付け、記録タブの一覧から修正対象を確認してください
- 収録数は現時点で、ボキャブラリー 74・音声変化 40（規則 8 種）・ビジネス表現 42・実務文法 18・会話 4 本です（要件定義の初期版の目標件数には未達）

## 学習コンテンツを追加する

コンテンツは `data/content/` の JSON ファイルです。既存の項目をまねて追記してください。

| ファイル | 内容 |
|----------|------|
| `vocabulary.json` | 単語・句動詞（見出し・品詞・意味・ニュアンス・コロケーション・例文と訳・タグ） |
| `connected_speech_rules.json` | 音声変化の規則（連結・脱落など）と解説 |
| `connected_speech.json` | 音声変化の例文（規則 ID・聞こえ方・紛らわしい選択肢） |
| `phrases.json` | 場面別のビジネス表現（場面・丁寧さ・意味・解説） |
| `grammar.json` | 実務文法の選択問題（選択肢・正解の番号・解説） |
| `dialogues.json` | 短い会話（話者ごとの行と訳） |

追記したら、次のコマンドで形式を確認します。

```bash
python -m pytest tests/test_content.py -q
```

期待される結果: `passed` と表示されます。ID の重複、未知の規則や場面、選択肢の不足などがあると、該当する項目の ID とともに失敗します。

## テスト

```bash
python -m pytest tests/ -q
```

GitHub Actions（`.github/workflows/test.yml`）でも、push と pull request のたびに同じテストを実行します。

## 構成

```
app.py                         # エントリポイント（タブの切り替え）
english_app/                   # 画面に依存しないロジック（pytest で検証）
  content.py                   # コンテンツの読み込みと検証
  srs.py / session.py          # 間隔反復と、時間制セッションの出題順
  quiz.py / dictation.py       # クイズと書き取りの出題
  text_match.py                # 正解文と入力文の照合（書き取り・発音・シャドーイングで共通）
  listening.py                 # 聞き流しの単元とプレイリスト
  progress.py / progress_store.py  # 学習履歴と保存先（Gist・ファイル・メモリ）
  config.py                    # Secrets の読み込みと保存先の決定
  ui/                          # Streamlit の部品（読み上げ・音声認識・ナビゲーションなど）
  views/                       # タブごとの画面
components/speech_recognizer/  # 音声認識を呼ぶ HTML/JS コンポーネント（ビルド不要）
data/content/                  # 学習コンテンツ（JSON）
tests/                         # pytest
```

## 依存関係

依存は Streamlit のみです（`requirements.txt`）。Gist との通信は Python 標準ライブラリで行います。`streamlit>=1.67` としているのは、埋め込み HTML に `st.iframe` を使っているためです（それ以前の `components.v1.html` は非推奨になりました）。表やグラフは Markdown と HTML で描いており、pyarrow を使う部品（`st.dataframe` など）は使っていません。

依存を更新したときは、`python -m pytest tests/ -q` と、ローカルでの起動（各タブが表示されること）を確認してください。
