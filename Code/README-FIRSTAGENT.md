# firstAgent 使用说明

目的：说明如何为 `firstAgent.py` 安装依赖并安全地配置运行所需的环境变量。

- 文件位置：`ProjectPractice/Code/firstAgent.py`

1) 安装依赖

在虚拟环境激活后运行：

```bash
pip install -r requirements.txt
```

2) 必要的环境变量

请不要在代码中写入明文密钥。运行前在环境中设置以下变量：

- `TAVILY_API_KEY`：Tavily 搜索 API Key
- `LLM_API_KEY`：你的 LLM 服务 Key（脚本中当前用到的 `API_KEY` 应替换为从此环境变量读取）
- `LLM_BASE_URL`：LLM 服务的 base URL（脚本中 `BASE_URL`）
- `LLM_MODEL_ID`：要使用的模型 ID（脚本中 `MODEL_ID`）

示例（PowerShell，临时会话）：

```powershell
$env:TAVILY_API_KEY = "tvly-your-key"
$env:LLM_API_KEY = "sk-your-llm-key"
$env:LLM_BASE_URL = "https://your-llm-endpoint.example/v1"
$env:LLM_MODEL_ID = "your-model-id"
python .\firstAgent.py
```

示例（Bash）：

```bash
export TAVILY_API_KEY="tvly-your-key"
export LLM_API_KEY="sk-your-llm-key"
export LLM_BASE_URL="https://your-llm-endpoint.example/v1"
export LLM_MODEL_ID="your-model-id"
python firstAgent.py
```

3) 建议的代码更新（可选，但强烈推荐）

- 在 `firstAgent.py` 中移除或注释掉任何硬编码的 `API_KEY` 或 `os.environ[...] = ...` 语句。
- 将脚本中 `API_KEY`, `BASE_URL`, `MODEL_ID` 等改为从环境变量读取，例如 `os.environ.get('LLM_API_KEY')`。
- 考虑使用 `python-dotenv` 在本地开发时从 `.env` 文件加载（不要把 `.env` 提交到版本库）。

4) 安全注意事项

- 不要把真实密钥提交到仓库或将它们硬编码在脚本中。
- 对敏感日志（包含完整 API 返回）进行脱敏或只在调试时输出。

如果你希望，我可以：

- 自动 patch `firstAgent.py` 以从环境变量读取 LLM 配置并移除硬编码示例；
- 或者再添加一个 `.env.example` 帮助你本地测试（示例不包含真实密钥）。
