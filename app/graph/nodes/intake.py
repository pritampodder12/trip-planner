from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.schemas.trip import TripRequest

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract trip details from the user's message. "
            "Never invent values. If something is not stated, leave it empty "
            "and add its name to missing info.",
        ),
        ("human", "{user_text}"),
    ]
)


@lru_cache
def get_chain():
    model = init_chat_model(
        settings.llm_model_id,
        model_provider="bedrock_converse",
        region_name=settings.aws_region,
        temperature=settings.llm_temperature,
    )
    return prompt | model.with_structured_output(TripRequest)


async def parse_trip_request(user_text: str) -> TripRequest:
    return await get_chain().ainvoke({"user_text": user_text})
