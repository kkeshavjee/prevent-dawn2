from typing import Callable
from fastapi import Depends, HTTPException
from .dependencies import CurrentUser, get_current_user

PATIENT = "patient"
ADMIN = "admin"
HEALTH_COACH = "health_coach"


def require_role(*roles: str) -> Callable:
    async def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _check
