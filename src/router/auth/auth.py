from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from router.auth.eugene_jwts import validate_eugene_access_token
from router.auth.conf import SECURITY


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),
):
    token = credentials.credentials
    return validate_eugene_access_token(token)
