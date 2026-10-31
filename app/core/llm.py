from functools import lru_cache

from langchain.chat_models import init_chat_model

from app.core.config import settings


@lru_cache
def get_llm():
    return init_chat_model(
        settings.llm_model_id,
        model_provider="bedrock_converse",
        region_name=settings.aws_region,
        temperature=settings.llm_temperature,
    )
