from fastmcp.server.auth.providers.jwt import JWTVerifier


def _generate_jwt_verifier(secret_key: str, iss: str, aud: str) -> JWTVerifier:
    # Use a shared secret for symmetric key verification
    verifier = JWTVerifier(
        public_key=secret_key, issuer=iss, audience=aud, algorithm="HS256"
    )
    return verifier
