# OAUTH EUGENE

This document captures information about how EUGENE uses OAUTH for single sign on.


## Identity vs Access
When discussing oauth and single sign on it is a good start to make the distinction between authentication (authn) vs authorization (authz).

Authn is used to verify an entity is who they say they are.

Authz is the act of determining what action or roles the entity can perform.


## Eugene identity and access

EUGENE connects to CSL Microsoft ENTRA ID to retrieve [ID tokens](https://learn.microsoft.com/en-us/entra/identity-platform/id-tokens). The ID token are then verified and parsed for basic identity information. Next an access token is generated to be used to access the APIs.

Access tokens are generated in `eugene_ws` endpoint. e.g. `https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/login`

The endpoint is meant to be accessed outside of the swagger documents, the access token is to be copied into the swagger document by clicking the "Authorize" and padlock icon.

Eugene oauth JWT tokens are generated in this [code](../src/router/). We use JWT HS256 for eugene generated tokens and entra ids use RS256. See, [HS256 vs RS256](https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/)


## Eugene configuration

Eugene requires oauth configuration variables for both entra id and eugene generated tokens.


.env sample

```
ENTRA_SCOPE=email
ENTRA_AUTHORITY=https://login.microsoftonline.com/e9ea0366-82a4-4b75-ab01-780fabc4c3c9
REDIRECT_URI=https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/auth/callback
REDIRECT_PATH=/auth/callback

ENTRA_TENANT_ID=e9ea0366-82a4-4b75-ab01-780fabc4c3c9
ENTRA_CLIENT_ID=76e3ed82-c161-4eaf-aa26-5b3ea7e2ab24
ENTRA_CLIENT_SECRET=<redacted>

EUGENE_TENANT_ID=f8645748-68c6-4eec-bd61-c71341a6ed7d
EUGENE_CLIENT_ID=ff58ded5-c309-4cc8-ae6a-3b7157b83879
EUGENE_CLIENT_SECRET=<redacted>
```

See the full list of env variables in the `difflabs` AWS account. Look in the secrets manager location with name `eugene/dev/uspto/env`.


## State of roles

Currently the roles are not used to verify read / write access to public / proprietary data. It is the goal to store proprietary data, but is not the case at the moment.

To store proprietary data would require.

1. easy task: Update users and [roles list](../src/router/auth/roles.py)
2. longer task: Update adapter classes and node data model to filter on nodes with a given permissions
3. longer task++: Move to a licensed neo4j that allows for more complex role management. Role features do not exist in the CE (community edition)