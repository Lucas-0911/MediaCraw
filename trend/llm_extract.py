# -*- coding: utf-8 -*-
import json
from typing import Optional

import httpx

from trend.extract import ProductMention, normalize_name, product_key_for
from trend.settings import get_settings

PROMPT = """You extract a sellable product name from short-video copy.
Return JSON only: {"name": "...", "confidence": 0.0}
If there is no clear physical product, return {"name": "", "confidence": 0}.
Copy:
"""


async def llm_guess_product(desc: str, comments: Optional[list] = None) -> Optional[ProductMention]:
    settings = get_settings()
    if not settings.get("TREND_LLM_ENABLED"):
        return None
    api_key = settings.get("TREND_LLM_API_KEY") or ""
    if not api_key:
        return None
    text = (desc or "").strip()
    if comments:
        text += "\nComments:\n" + "\n".join(str(c) for c in comments[:8])
    if len(text) < 8:
        return None
    url = str(settings.get("TREND_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    payload = {
        "model": settings.get("TREND_LLM_MODEL") or "gpt-4o-mini",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You output JSON only."},
            {"role": "user", "content": PROMPT + text[:2000]},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except Exception:
        return None
    name = str(parsed.get("name") or "").strip()
    confidence = float(parsed.get("confidence") or 0)
    if not name or confidence < 0.5:
        return None
    norm = normalize_name(name)
    if len(norm) < 2:
        return None
    return ProductMention(
        product_key=product_key_for(None, name),
        name=name,
        identity_type="llm",
        source="llm",
    )
