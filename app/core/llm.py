from functools import lru_cache

from app.core.config import settings


def _make_bedrock_llm():
    from langchain.chat_models import init_chat_model

    print("bedrock llm called")
    return init_chat_model(
        settings.llm_model_id,
        model_provider="bedrock_converse",
        region_name=settings.aws_region,
        temperature=settings.llm_temperature,
    )


def _make_azure_llm():
    from langchain_openai import ChatOpenAI

    print("azure llm called!")
    return ChatOpenAI(
        model=settings.azure_openai_deployment,
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        reasoning_effort="minimal",  # "minimal" | "low" | "medium" | "high"
        verbosity="low",
        temperature=settings.llm_temperature,
    )


_LLM_FACTORY = {
    "bedrock": _make_bedrock_llm,
    "azure": _make_azure_llm,
}


@lru_cache
def get_llm():
    provider = settings.llm_provider
    factory = _LLM_FACTORY.get(provider)
    if factory is None:
        supported = ", ".join(_LLM_FACTORY.keys())
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Supported values: {supported}"
        )
    return factory()
