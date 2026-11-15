from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    weather_mock: bool = False

    # Provider selector — set LLM_PROVIDER in .env to switch
    llm_provider: str = "bedrock"

    # Bedrock settings
    aws_region: str = "ap-south-1"
    llm_model_id: str = ""

    # Azure AI Foundry settings
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""

    llm_temperature: float = 0.2

    checkpoint_db: str = "data/checkpoints.db"
    log_level: str = "INFO"


settings = Settings()
