from typing import Optional

from fastapi import HTTPException

from core.config import API_KEY


def require_api_key(x_api_key: Optional[str]):
    if not API_KEY:
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")
