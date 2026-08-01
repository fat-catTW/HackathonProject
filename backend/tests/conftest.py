"""測試一律跑本地 mock 模式。

專案根目錄的 .env 目前是 USE_MOCK=false（連真實 DynamoDB / Bedrock / AgentCore），
若不強制覆蓋，跑一次測試就會把假案件寫進共用的 ServiceAssistant 表。這裡在
app.config 載入 .env 之前先設好環境變數；config 的 load_dotenv 是 override=False，
因此這些值會勝出。

AWS 憑證同理要清空：llm.has_aws_credentials() 不看 USE_MOCK，只要環境裡有一組能用
的憑證（IAM 三件套或 Bedrock API key），測試就會真的打 Bedrock，變成非決定性、還會
撞 rate limit。backend/.env 放真的憑證是本機開發常態，測試環境必須主動蓋掉。
"""
import os

os.environ["USE_MOCK"] = "true"
os.environ["AGENT_TOOL_MODE"] = "embedded"
os.environ["AGENTCORE_MEMORY_ID"] = ""
os.environ["AGENTCORE_GATEWAY_URL"] = ""
os.environ["AWS_ACCESS_KEY_ID"] = ""
os.environ["AWS_SECRET_ACCESS_KEY"] = ""
os.environ["AWS_SESSION_TOKEN"] = ""
os.environ["AWS_PROFILE"] = ""
os.environ["AWS_BEARER_TOKEN_BEDROCK"] = ""
os.environ["GEMINI_API_KEY"] = ""
