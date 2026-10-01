import logging

from fastapi import APIRouter, Depends

from router.auth.auth import get_current_user

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    tags=["auth"],
)


@router.get("/auth/whoami")
def protected(user: dict = Depends(get_current_user)):
    return {"user": user}
