import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    kis_app_key: str = os.getenv("KIS_APP_KEY", "")
    kis_app_secret: str = os.getenv("KIS_APP_SECRET", "")
    kis_account_no: str = os.getenv("KIS_ACCOUNT_NO", "")
    kis_account_num: str = os.getenv("KIS_ACCOUNT_NUM", os.getenv("KIS_ACCOUNT_NO", ""))
    kis_base_url: str = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    stock_cache_file: str = os.getenv("STOCK_CACHE_FILE", str(BASE_DIR / "stocks_cache.json"))
    token_cache_file: str = os.getenv("TOKEN_CACHE_FILE", str(BASE_DIR / "token_cache.json"))
    # 임시 DB 설정 - 실제로는 .env 파일에서 읽어야 함
    db_host: str = os.getenv("DB_HOST", "knhanul.nuni.co.kr")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_name: str = os.getenv("DB_NAME", "stock")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "posid00")
    db_sslmode: str = os.getenv("DB_SSLMODE", "prefer")


settings = Settings()
