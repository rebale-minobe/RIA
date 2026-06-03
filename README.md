# 🌟 RIA — Ria's Intelligent Agent

莉亜さん専用の学習エージェント。Streamlit + Claude API で構築。

## 機能（MVP v0.1）

- 📘 国語・🗺️ 社会・📐 数学・🔬 理科・🌐 英語 — 教科別AIチューター
- 📅 テストスケジュール — 期末範囲・14日間学習計画
- 📷 教材の写真アップロード対応（Claude vision）
- ✅ 学習タスクのチェック管理

## セットアップ

### 1. ローカルで動かす

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml を編集して ANTHROPIC_API_KEY を記入
streamlit run app.py
```

### 2. Streamlit Cloud にデプロイ

1. [share.streamlit.io](https://share.streamlit.io) にログイン
2. New app → リポジトリ `rebale-minobe/RIA` を選択
3. Branch: `main`、Main file path: `app.py`
4. Deploy → ビルドが終わったら **Settings → Secrets** へ
5. 以下を貼り付け（実際のキー値を記入）:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

6. Save → 数十秒で再起動 → 完成

## ディレクトリ構成

```
RIA/
├── app.py                    # ホーム画面
├── pages/                    # 各教科 + スケジュール
├── shared/                   # 共通機能
│   ├── claude_client.py      # Claude API
│   ├── profile.py            # 学習者プロファイル
│   ├── storage.py            # 永続化
│   └── ui.py                 # 教科ページ共通テンプレート
├── modules/                  # 教科別ロジック
│   ├── japanese/
│   ├── social/
│   ├── math/                 # ← 最重要
│   ├── science/
│   ├── english/
│   └── schedule/
└── data/                     # プロファイル＋スケジュール
```

## 設計原則

1. 答えを教えるより、**自分の言葉で説明させる**エージェント
2. **トーンは伴走**、間違いは「発見」として扱う
3. **本人の自走を奪わない**（紙の学習計画表のデジタル拡張）
4. **家族の長期資産**として育てる（源也・結衣にも展開可能）

## Phase 2以降の予定

- 漢字テスト問題集の自動生成（毎週）
- 各教科の小テスト対策
- 音声入出力（Whisper + TTS）
- streak機能・学習履歴可視化
- 英検準2級モジュール
- データ永続化を ria-data リポジトリへ
- 志望校選抜サポート
- 高校入試対策

## ライセンス

Private — 見延家専用。
