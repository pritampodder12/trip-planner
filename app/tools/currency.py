import logging

import httpx
from langchain_core.tools import tool

from app.core.logging_config import log_call
from app.tools.geo import HEADERS

logger = logging.getLogger(__name__)


@tool
@log_call("tool", log_args=True)
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount between two currencies using the latest ECB reference
    rates, for example amount=500, from_currency='USD', to_currency='INR'."""
    # logger.info("[tool] convert_currency | amount=%s from=%r to=%r", amount, from_currency, to_currency)
    src, dst = from_currency.upper(), to_currency.upper()
    try:
        async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
            r = await client.get(
                "https://api.frankfurter.dev/v1/latest",
                params={"amount": amount, "base": src, "symbols": dst},
            )
            r.raise_for_status()
        data = r.json()
        return f"{amount} {src} = {data['rates'][dst]} {dst} (ECB rate dated {data['date']})"
    except (httpx.HTTPError, KeyError) as e:
        return f"Could not convert {src} to {dst}: {e}"
