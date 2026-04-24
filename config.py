import os

class Settings:
    def __init__(self):
        self.DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
        self.DEEPSEEK_MODEL = "deepseek-coder"  # Best for code
        self.DEEPSEEK_TIMEOUT = 120

        self.GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
        self.DATABASE_URL = "sqlite+aiosqlite:///studio.db"
        self.PORT = int(os.environ.get("PORT", "5000"))
        self.HOST = "0.0.0.0"

settings = Settings()

if settings.DEEPSEEK_API_KEY and "your_key" not in settings.DEEPSEEK_API_KEY:
    print("✅ DeepSeek API key loaded")
else:
    print("⚠️  DeepSeek API key not configured - Add to Secrets")

if settings.GITHUB_TOKEN and "your_token" not in settings.GITHUB_TOKEN:
    print("✅ GitHub token loaded")
else:
    print("⚠️  GitHub token not configured - Add to Secrets")