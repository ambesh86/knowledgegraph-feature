import logging

from router.auth.const import (
    EUGENE_TENANT_ID,
    EUGENE_USER_CONFIDENTIAL_READ_ROLE,
    EUGENE_USER_PUBLIC_READ_ROLE,
)


logger = logging.getLogger(__name__)


def _composite_role_key(upn: str, tenant_id: str = EUGENE_TENANT_ID) -> str:
    return f"{tenant_id}|{upn}"


USER_ROLE_MAP = {
    _composite_role_key("PingAMS.TestTen@cslgqa.net"): [EUGENE_USER_PUBLIC_READ_ROLE],
    _composite_role_key("Damian.Knopp@cslbehring.com"): [
        EUGENE_USER_PUBLIC_READ_ROLE,
        EUGENE_USER_CONFIDENTIAL_READ_ROLE,
    ],
    _composite_role_key("Sterling.Foster@cslbehring.com"): [
        EUGENE_USER_PUBLIC_READ_ROLE,
        EUGENE_USER_CONFIDENTIAL_READ_ROLE,
    ],
    _composite_role_key("Paul.Disney@cslbehring.com"): [
        EUGENE_USER_PUBLIC_READ_ROLE,
        EUGENE_USER_CONFIDENTIAL_READ_ROLE,
    ],
}

DEFAULT_ROLES = frozenset([EUGENE_USER_PUBLIC_READ_ROLE])


def load_roles_for_user(upn: str) -> list[str]:
    """
    load_roles_for_user

    :param tenant_id: oidc application tenant id
    :type tenant_id: str
    :param upn: user id
    :return: unique list of roles
    :rtype: list[str]
    """

    current_user = _composite_role_key(upn=upn)
    if current_user in USER_ROLE_MAP:
        user_roles = frozenset(USER_ROLE_MAP[current_user])
        roles = set(DEFAULT_ROLES)
        user_roles = roles.union(user_roles)
    else:
        # todo: default to principle of least privilege; deny all roles from unknown users after we add non public data
        logger.info(f"{current_user} not found in roles map. Applying default roles...")
        user_roles = frozenset(set())
        roles = set(DEFAULT_ROLES)
        user_roles = roles.union(user_roles)

    logger.info(f"user: {current_user}, applying roles: {user_roles}")
    return list(user_roles)


def load_roles_for_local_development() -> list[str]:
    return list(DEFAULT_ROLES)
