#!/bin/bash
# aider-local launcher（由 deploy-aider 從此範本渲染後佈署到各機）
# Renders to a per-fleet launcher that points aider at your LOCAL LLM server.
# 佔位符會在佈署時被 config/local-ai.env 的值取代。

export OPENAI_API_BASE="__OPENAI_API_BASE__"
export OPENAI_API_KEY="__OPENAI_API_KEY__"

# 解析使用者本地 python 安裝的 aider
AIDER_BIN="aider"
if [ -f "$HOME/Library/Python/3.9/bin/aider" ]; then
  AIDER_BIN="$HOME/Library/Python/3.9/bin/aider"
fi

exec "$AIDER_BIN" --model "__MODEL__" --no-show-model-warnings --edit-format diff "$@"
