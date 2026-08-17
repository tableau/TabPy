import logging
import threading
import time

import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

# PyJWKClient fetches JWKS synchronously (via requests). On the HTTP path
# that call runs on TabPy's single Tornado IO-loop thread, so a
# slow/unresponsive IdP stalls every concurrent HTTP request for up to this
# many seconds. Caching (see _jwks_clients) bounds how often this happens.
# A cold start or legitimate key rotation still pays this cost.
JWKS_FETCH_TIMEOUT_SECONDS = 10

# Bounds how long a JWT check waits for _jwks_lock. Arrow Flight auth runs
# on the gRPC thread pool and HTTP auth runs on the Tornado IO loop, and
# both share the lock, so without a bound an unauthenticated Flight caller
# could force a slow JWKS fetch and stall every HTTP request behind it for
# up to JWKS_FETCH_TIMEOUT_SECONDS. Callers that time out waiting fail
# closed instead; a responsive IdP resolves well inside this window.
JWKS_LOCK_WAIT_SECONDS = 1

# An unauthenticated caller can force a fresh JWKS fetch just by sending a
# made-up `kid` (read from the token header pre-signature-check). This
# bounds, per jwks_uri, how often a *failed* forced refresh (kid still not
# found) can refetch again. Only failures set the cooldown -- a successful
# refresh (e.g. a genuine key rotation) must not be penalized. Also used
# to rate-limit retrying a JWKS endpoint that just failed to fetch at all
# (network error, timeout, malformed response), so a down/unreachable IdP
# can't be hammered with a fresh blocking fetch on every single request.
JWKS_MIN_REFRESH_INTERVAL_SECONDS = 30

# One PyJWKClient per JWKS URI, reused so its JWK Set cache actually avoids
# per-request fetches. Process-global; mutations are serialized by
# _jwks_lock because HTTP (IO-loop) and Arrow Flight (gRPC thread pool)
# share these dicts.
_jwks_lock = threading.Lock()
_jwks_clients = {}

# jwks_uri -> monotonic timestamp of the last failed JWKS fetch (network
# error, timeout, malformed response -- not a kid mismatch). Rate-limits
# retrying a broken/unreachable IdP, independent of which kid was
# requested: every such failure means the fetch itself never completed, so
# nothing in the cache could satisfy any kid anyway.
_jwks_last_fetch_failure = {}

# jwks_uri -> monotonic timestamp of the last forced refresh that fetched
# successfully but still didn't find the requested kid. Keyed only by
# jwks_uri, not by kid: the kid is read from the token header before the
# signature is checked, so it's fully attacker-controlled. Keying by kid
# would let an attacker force a fresh blocking JWKS fetch on every request
# just by varying the kid -- an unauthenticated DoS. The tradeoff is that a
# bogus kid can delay visibility of a legitimately rotated key by up to
# JWKS_MIN_REFRESH_INTERVAL_SECONDS, which is an acceptable bound.
_jwks_last_failed_refresh = {}


def _get_jwks_client(jwks_uri: str) -> PyJWKClient:
    client = _jwks_clients.get(jwks_uri)
    if client is None:
        client = PyJWKClient(
            jwks_uri, cache_jwk_set=True, timeout=JWKS_FETCH_TIMEOUT_SECONDS
        )
        _jwks_clients[jwks_uri] = client
    return client


def _fetch_signing_keys(jwks_client: PyJWKClient, jwks_uri: str, refresh: bool):
    now = time.monotonic()
    last_failure = _jwks_last_fetch_failure.get(jwks_uri, 0)
    if now - last_failure < JWKS_MIN_REFRESH_INTERVAL_SECONDS:
        raise jwt.exceptions.PyJWKClientError(
            f'JWKS endpoint "{jwks_uri}" failed recently; not retrying yet'
        )
    try:
        return jwks_client.get_signing_keys(refresh=refresh)
    except Exception:
        _jwks_last_fetch_failure[jwks_uri] = now
        raise


def _get_signing_key(jwks_client: PyJWKClient, jwks_uri: str, token: str):
    """
    Resolves the signing key for `token`'s `kid`, same as
    PyJWKClient.get_signing_key_from_jwt(), except the cache-miss retry is
    rate-limited per jwks_uri (see JWKS_MIN_REFRESH_INTERVAL_SECONDS)
    instead of firing unconditionally.
    """
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    signing_keys = _fetch_signing_keys(jwks_client, jwks_uri, refresh=False)
    signing_key = PyJWKClient.match_kid(signing_keys, kid)
    if signing_key is not None:
        return signing_key

    now = time.monotonic()
    last_failure = _jwks_last_failed_refresh.get(jwks_uri, 0)
    if now - last_failure < JWKS_MIN_REFRESH_INTERVAL_SECONDS:
        raise jwt.exceptions.PyJWKClientError(
            f"Unable to find a signing key that matches: {kid!r}"
        )

    signing_keys = _fetch_signing_keys(jwks_client, jwks_uri, refresh=True)
    signing_key = PyJWKClient.match_kid(signing_keys, kid)
    if signing_key is None:
        _jwks_last_failed_refresh[jwks_uri] = now
        raise jwt.exceptions.PyJWKClientError(
            f"Unable to find a signing key that matches: {kid!r}"
        )
    return signing_key


class JwtValidationError(Exception):
    """Raised when a JWT Bearer token fails validation."""


def validate_jwt(
    token: str,
    issuer: str,
    jwks_uri: str,
    audience: str,
    required_scopes: str = None,
) -> dict:
    """
    Validates a JWT Bearer token's signature, issuer, audience, expiry,
    and not-before claims, plus optional required scopes.

    Parameters
    ----------
    token : str
        The raw JWT (without the "Bearer " prefix).
    issuer : str
        Expected `iss` claim.
    jwks_uri : str
        JWKS endpoint used to resolve the token's signing key.
    audience : str
        Expected `aud` claim.
    required_scopes : str, optional
        Comma-separated scopes that must all be present in the token's
        `scope` claim. Skipped if None or empty.

    Returns
    -------
    dict
        The decoded JWT claims.

    Raises
    ------
    JwtValidationError
        If the token is missing, malformed, expired, or fails any of
        the signature/issuer/audience/scope checks.
    """
    if not token:
        raise JwtValidationError("Missing JWT")

    try:
        if not _jwks_lock.acquire(timeout=JWKS_LOCK_WAIT_SECONDS):
            raise jwt.exceptions.PyJWKClientError(
                f'Timed out waiting on an in-flight JWKS fetch for "{jwks_uri}"'
            )
        try:
            jwks_client = _get_jwks_client(jwks_uri)
            signing_key = _get_signing_key(jwks_client, jwks_uri, token)
        finally:
            _jwks_lock.release()
    except (jwt.exceptions.PyJWKClientError, jwt.exceptions.InvalidTokenError) as ex:
        logger.log(logging.ERROR, f"Unable to resolve JWT signing key: {str(ex)}")
        raise JwtValidationError("Unable to resolve JWT signing key") from ex
    except Exception as ex:
        # Must still surface as a 401, not a 500 (e.g. malformed JWKS response).
        logger.log(logging.ERROR, f"Unexpected error resolving JWT signing key: {str(ex)}")
        raise JwtValidationError("Unable to resolve JWT signing key") from ex

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "iat"]},
        )
    except jwt.exceptions.InvalidTokenError as ex:
        logger.log(logging.ERROR, f"JWT validation failed: {str(ex)}")
        raise JwtValidationError(f"JWT validation failed: {str(ex)}") from ex
    except Exception as ex:
        # Must still fail closed as a 401 / UNAUTHENTICATED, not a 500
        # or an ArrowInvalid traceback to an unauthenticated caller.
        logger.log(logging.ERROR, f"Unexpected error decoding JWT: {str(ex)}")
        raise JwtValidationError("JWT validation failed") from ex

    if required_scopes:
        try:
            _check_scopes(claims, required_scopes)
        except JwtValidationError:
            raise
        except Exception as ex:
            # Must still fail closed as a 401 (e.g. a `scope` claim that
            # isn't a space-separated string), not an uncaught 500.
            logger.log(logging.ERROR, f"Unable to evaluate JWT scopes: {str(ex)}")
            raise JwtValidationError("Unable to evaluate JWT scopes") from ex

    return claims


def _check_scopes(claims: dict, required_scopes: str) -> None:
    granted = set(claims.get("scope", "").split())
    missing = [
        s for s in (s.strip() for s in required_scopes.split(","))
        if s and s not in granted
    ]
    if missing:
        raise JwtValidationError(f"JWT missing required scope(s): {', '.join(missing)}")
