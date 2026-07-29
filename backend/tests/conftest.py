"""測試一律跑本地 mock 模式。

專案根目錄的 .env 目前是 USE_MOCK=false（連真實 DynamoDB / Bedrock / AgentCore），
若不強制覆蓋，跑一次測試就會把假案件寫進共用的 ServiceAssistant 表。這裡在
app.config 載入 .env 之前先設好環境變數；config 的 load_dotenv 是 override=False，
因此這些值會勝出。
"""
import os

os.environ["USE_MOCK"] = "true"
os.environ["AGENT_TOOL_MODE"] = "embedded"
os.environ["AGENTCORE_MEMORY_ID"] = ""
os.environ["AGENTCORE_GATEWAY_URL"] = ""
