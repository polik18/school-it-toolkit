# 🤖 本地 AI 工作站與機房 AI 助手

> 在校內架一台「本地 LLM 伺服器」，讓全機房的電腦都能用免費、隱私、不需上雲的 AI 寫程式助手。
> 適合資訊課程：學生可在課堂用 AI 輔助學習，資料不外流、無 API 費用。

---

## 0. 架構概念

```
  [本地 AI 伺服器]  ←(OpenAI 相容 API)→  [機房各電腦的 aider / Cursor / Claude Code]
   一台較強的 Mac                              學生端，透過 aider-local 啟動器連回伺服器
```

- **伺服器**：一台統一記憶體較大的 Apple Silicon Mac（如 Mac Studio），跑本地推理服務。
- **推理服務**：任何 **OpenAI 相容**的本地服務皆可（例如 oMLX、Ollama、LM Studio）。
- **客戶端**：機房各機裝 `aider`，透過本工具佈署的 `aider-local` 啟動器自動連回伺服器。

---

## 1. 伺服器端（範例：oMLX）

> 以下以 oMLX 為例；換成 Ollama/LM Studio 概念相同：啟動一個 OpenAI 相容端點即可。

重點設定（依你的機器記憶體調整）：
- **端點**：`http://<伺服器IP>:8000/v1`，啟用 API Key 驗證。
- **記憶體防護**：大模型載入若報記憶體上限錯誤（memory ceiling），把防護層級調為較寬鬆的
  `conservative`（見 [`pitfalls.md`](pitfalls.md) 思路相同的資源權衡）。
- **工具調用穩定性**：本地模型做 agent 時若常 JSON 解析錯誤，啟用文法約束解碼（如 oMLX 的
  `xgrammar`）可強制輸出符合 tool-calling 語法。
- **驗證端點**：
  ```bash
  curl -H "Authorization: Bearer <你的API_KEY>" http://<伺服器IP>:8000/v1/models
  ```

> 🔐 **不要把真實端點 IP 與 API Key 寫進 repo**。它們只放 `config/local-ai.env`（gitignored）。

---

## 2. 客戶端佈署（機房各機）

### 步驟一：填寫本地 AI 設定
```bash
cp config/local-ai.env.example config/local-ai.env
# 編輯填入：
#   LOCAL_LLM_API_BASE="http://<伺服器IP>:8000/v1"
#   LOCAL_LLM_API_KEY="<你的key>"
#   LOCAL_LLM_MODEL="openai/<你的模型名>"
#   TARGET_USER="user"   # 學生帳號
```

### 步驟二：佈署 aider + 啟動器
（前提：已先用 `school-brew` 佈署好 Homebrew 與 pip wrapper）
```bash
tools/local-ai/deploy-aider --group all
```
這會在每台機器：以學生帳號 `pip install aider-chat`，並安裝 `/usr/local/bin/aider-local`
啟動器（由 `remote/aider-local.template.sh` **用你的 config 值即時渲染**，repo 內不含端點/金鑰）。

### 步驟三：學生使用
學生在終端機任一專案目錄輸入：
```bash
aider-local
```
即自動連回校內本地模型，開始 AI 輔助寫程式。

---

## 3. 地雷與避法
- **pip 權限錯誤**：先用 `school-brew` 佈署 pip wrapper（自動補 `--user`），見 [`homebrew-fleet.md`](homebrew-fleet.md)。
- **aider 預設找 `gpt-4o` 報 not found**：因為連到本地端點卻請求雲端模型名。啟動器已固定
  `--model <你的本地模型>` 解決；這也是為何用 `aider-local` 而非裸 `aider`。
- **記憶體不足**：同時載入多個大模型會吃滿 wired memory，必要時只載一個模型或降低 context window。

## 4. 相關
- `config/local-ai.env.example`、`tools/local-ai/deploy-aider`
- [`homebrew-fleet.md`](homebrew-fleet.md)（前置）
