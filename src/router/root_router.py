from fastapi import APIRouter, Depends

from router.auth.auth import get_current_user

router = APIRouter(
    prefix="",
    tags=["root"],
)


@router.get("/")
async def app_root(user: dict = Depends(get_current_user)):
    return {"message": "Welcome to the euGENE API (+Microsoft Entra ID)!", "user": user}
