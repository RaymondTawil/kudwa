from __future__ import annotations
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    db_path: str = os.getenv("DB_PATH", "app/db/finance_ai.db")
    auto_ingest: bool = os.getenv("AUTO_INGEST", "0") == "1"
    qb_file: str = os.getenv("QB_FILE", "/test_data/data_set_1.json")
    rootfi_file: str = os.getenv("ROOTFI_FILE", "/test_data/data_set_2.json")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    model_name: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    model_variants: str = os.getenv('MODEL_VARIANTS', 'gpt-4o-mini,gpt-4o')


settings = Settings()