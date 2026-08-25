import threading
import time

import jwt
from jwt import PyJWKClient

# PyJWKClient fetches JWKS synchronously (via requests). On the HTTP path
# that call runs on TabPy's single Tornado IO-loop thread, so a
# slow/unresponsive IdP stalls every concurrent HTTP request for up to this
# many seconds. Caching (see _jwks_clients) bounds how often this happens.
# A cold start or legitimate key rotation still pays this cost.
JWKS_FETCH_TIMEOUT_SECONDS = 10

# An unauthenticated caller can force a fresh JWKS fetch just by sending a
# made-up `kid` (read from the token header pre-signature-check). This
# bounds, per jwks_uri, how often a *failed* forced refresh (kid still not
# found) can refetch again. Only failures set the cooldown -- a successful
# refresh (e.g. a genuine key rotation) must not be penalized. Also used
# to rate-limit retrying a JWKS endpoint that just failed to fetch at all
# (network error, timeout, malformed response), so a down/unreachable IdP
# can't be hammered with a fresh blocking fetch on every single request.
JWKS_MIN_REFRESH_INTERVAL_SECONDS = 30

# Matches PyJWKClient's default JWK Set cache lifespan. After this, the
# next lookup treats the snapshot as expired and single-flights one fetch.
JWKS_CACHE_LIFESPAN_SECONDS = 300

# Concurrent requests for the same newly published kid may briefly wait for
# the refresh owner instead of failing spuriously. Keep the wait short and
# bounded so this synchronous helper cannot tie up an HTTP or Flight worker
# for the full IdP fetch timeout.
JWKS_REFRESH_WAIT_SECONDS = 1

# One PyJWKClient per JWKS URI, reused so its JWK Set cache actually avoids
# per-request fetches. Process-global. _jwks_state_lock only covers these
# dicts. A per-URI fetch lock serializes cache-miss fetches and forced
# refreshes for that IdP. Warm (unexpired) kid lookups do not take that
# fetch lock, so a refresh cannot reject unrelated valid tokens.
_jwks_state_lock = threading.Lock()
_jwks_fetch_locks = {}
_jwks_clients = {}

# jwks_uri -> (kid, completion event). Reserving refresh ownership under
# _jwks_state_lock closes the race between taking the fetch lock and
# publishing which kid is being refreshed. Same-kid callers may wait for
# the owner; other unknown kids fail fast and cannot amplify JWKS traffic.
_jwks_in_flight_refreshes = {}

# jwks_uri -> (signing_keys, monotonic timestamp). Lets a warm cache
# return keys without waiting on another thread's in-flight fetch.
_jwks_cached_keys = {}

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
    with _jwks_state_lock:
        client = _jwks_clients.get(jwks_uri)
        if client is None:
            client = PyJWKClient(
                jwks_uri,
                cache_jwk_set=True,
                lifespan=JWKS_CACHE_LIFESPAN_SECONDS,
                timeout=JWKS_FETCH_TIMEOUT_SECONDS,
            )
            _jwks_clients[jwks_uri] = client
        return client


def _fetch_lock_for(jwks_uri: str) -> threading.Lock:
    with _jwks_state_lock:
        lock = _jwks_fetch_locks.get(jwks_uri)
        if lock is None:
            lock = threading.Lock()
            _jwks_fetch_locks[jwks_uri] = lock
        return lock


def _recently_recorded(store: dict, jwks_uri: str) -> bool:
    with _jwks_state_lock:
        last = store.get(jwks_uri)
    return (
        last is not None
        and time.monotonic() - last < JWKS_MIN_REFRESH_INTERVAL_SECONDS
    )


def _record_now(store: dict, jwks_uri: str) -> None:
    with _jwks_state_lock:
        store[jwks_uri] = time.monotonic()


def _read_cached_keys(jwks_uri: str):
    with _jwks_state_lock:
        entry = _jwks_cached_keys.get(jwks_uri)
        if entry is None:
            return None
        keys, fetched_at = entry
        if time.monotonic() - fetched_at >= JWKS_CACHE_LIFESPAN_SECONDS:
            return None
        return keys


def _write_cached_keys(jwks_uri: str, keys) -> None:
    if not keys:
        return
    with _jwks_state_lock:
        _jwks_cached_keys[jwks_uri] = (list(keys), time.monotonic())


def _fetch_failed_recently_error(jwks_uri: str) -> jwt.exceptions.PyJWKClientError:
    return jwt.exceptions.PyJWKClientError(
        f'JWKS endpoint "{jwks_uri}" failed recently; not retrying yet'
    )


def _call_get_signing_keys(jwks_client: PyJWKClient, jwks_uri: str, refresh: bool):
    if _recently_recorded(_jwks_last_fetch_failure, jwks_uri):
        raise _fetch_failed_recently_error(jwks_uri)
    try:
        keys = jwks_client.get_signing_keys(refresh=refresh)
    except Exception:
        _record_now(_jwks_last_fetch_failure, jwks_uri)
        raise
    _write_cached_keys(jwks_uri, keys)
    return keys


def _fetch_signing_keys(jwks_client: PyJWKClient, jwks_uri: str):
    cached = _read_cached_keys(jwks_uri)
    if cached is not None:
        # Warm cache. Must not wait on another thread's refresh, or a
        # forged unknown kid can reject valid tokens on HTTP and Flight.
        return cached

    # Cold or expired snapshot: single-flight one outbound fetch so
    # concurrent Flight threads cannot each pay JWKS_FETCH_TIMEOUT.
    if _recently_recorded(_jwks_last_fetch_failure, jwks_uri):
        raise _fetch_failed_recently_error(jwks_uri)

    fetch_lock = _fetch_lock_for(jwks_uri)
    fetch_lock.acquire()
    try:
        cached = _read_cached_keys(jwks_uri)
        if cached is not None:
            return cached
        return _call_get_signing_keys(jwks_client, jwks_uri, refresh=False)
    finally:
        fetch_lock.release()


def _refresh_signing_key(
    jwks_client: PyJWKClient, jwks_uri: str, kid
):
    if _recently_recorded(_jwks_last_fetch_failure, jwks_uri):
        raise _fetch_failed_recently_error(jwks_uri)
    if _recently_recorded(_jwks_last_failed_refresh, jwks_uri):
        raise jwt.exceptions.PyJWKClientError(
            f"Unable to find a signing key that matches: {kid!r}"
        )

    with _jwks_state_lock:
        in_flight = _jwks_in_flight_refreshes.get(jwks_uri)
        if in_flight is None:
            refresh_done = threading.Event()
            _jwks_in_flight_refreshes[jwks_uri] = (kid, refresh_done)
            owns_refresh = True
        else:
            in_flight_kid, refresh_done = in_flight
            owns_refresh = False

    if not owns_refresh:
        if in_flight_kid != kid:
            raise jwt.exceptions.PyJWKClientError(
                f'JWKS refresh already in flight for "{jwks_uri}"'
            )
        if not refresh_done.wait(JWKS_REFRESH_WAIT_SECONDS):
            raise jwt.exceptions.PyJWKClientError(
                f'JWKS refresh timed out for "{jwks_uri}"'
            )
        signing_keys = _read_cached_keys(jwks_uri)
        signing_key = (
            PyJWKClient.match_kid(signing_keys, kid)
            if signing_keys is not None
            else None
        )
        if signing_key is not None:
            return signing_key
        raise jwt.exceptions.PyJWKClientError(
            f"Unable to find a signing key that matches: {kid!r}"
        )

    fetch_lock = _fetch_lock_for(jwks_uri)
    acquired = fetch_lock.acquire(timeout=JWKS_REFRESH_WAIT_SECONDS)
    if not acquired:
        with _jwks_state_lock:
            current = _jwks_in_flight_refreshes.get(jwks_uri)
            if current is not None and current[1] is refresh_done:
                _jwks_in_flight_refreshes.pop(jwks_uri)
        refresh_done.set()
        raise jwt.exceptions.PyJWKClientError(
            f'JWKS refresh already in flight for "{jwks_uri}"'
        )
    try:
        # Refresh ownership includes key matching and cooldown publication.
        # No sibling can fetch between a mismatch and recording its cooldown.
        if _recently_recorded(_jwks_last_fetch_failure, jwks_uri):
            raise _fetch_failed_recently_error(jwks_uri)
        if _recently_recorded(_jwks_last_failed_refresh, jwks_uri):
            raise jwt.exceptions.PyJWKClientError(
                f"Unable to find a signing key that matches: {kid!r}"
            )

        signing_keys = _call_get_signing_keys(
            jwks_client, jwks_uri, refresh=True
        )
        signing_key = PyJWKClient.match_kid(signing_keys, kid)
        if signing_key is None:
            _record_now(_jwks_last_failed_refresh, jwks_uri)
            raise jwt.exceptions.PyJWKClientError(
                f"Unable to find a signing key that matches: {kid!r}"
            )
        return signing_key
    finally:
        fetch_lock.release()
        with _jwks_state_lock:
            current = _jwks_in_flight_refreshes.get(jwks_uri)
            if current is not None and current[1] is refresh_done:
                _jwks_in_flight_refreshes.pop(jwks_uri)
        refresh_done.set()


def _get_signing_key(jwks_client: PyJWKClient, jwks_uri: str, token: str):
    """
    Resolves the signing key for `token`'s `kid`, same as
    PyJWKClient.get_signing_key_from_jwt(), except the cache-miss retry is
    rate-limited per jwks_uri (see JWKS_MIN_REFRESH_INTERVAL_SECONDS)
    instead of firing unconditionally.
    """
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    signing_keys = _fetch_signing_keys(jwks_client, jwks_uri)
    signing_key = PyJWKClient.match_kid(signing_keys, kid)
    if signing_key is not None:
        return signing_key

    return _refresh_signing_key(jwks_client, jwks_uri, kid)


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
        jwks_client = _get_jwks_client(jwks_uri)
        signing_key = _get_signing_key(jwks_client, jwks_uri, token)
    except (jwt.exceptions.PyJWKClientError, jwt.exceptions.InvalidTokenError) as ex:
        raise JwtValidationError(
            f"Unable to resolve JWT signing key: {str(ex)}"
        ) from ex
    except Exception as ex:
        # Must still surface as a 401, not a 500 (e.g. malformed JWKS response).
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
        raise JwtValidationError(f"JWT validation failed: {str(ex)}") from ex
    except Exception as ex:
        # Must still fail closed as a 401 / UNAUTHENTICATED, not a 500
        # or an ArrowInvalid traceback to an unauthenticated caller.
        raise JwtValidationError("JWT validation failed") from ex

    if required_scopes:
        try:
            _check_scopes(claims, required_scopes)
        except JwtValidationError:
            raise
        except Exception as ex:
            # Must still fail closed as a 401 (e.g. a `scope` claim that
            # isn't a space-separated string), not an uncaught 500.
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


# Well-known endpoint scopes. Bound to HTTP paths when
# TABPY_OAUTH_ENFORCE_ENDPOINT_SCOPES is true. Not admin-defined.
SCOPE_QUERY = "tabpy:query"
SCOPE_EVALUATE = "tabpy:evaluate"
SCOPE_DEPLOY = "tabpy:deploy"

_MUTATING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

# Path rules in advertised-scope order. A None method set applies to every method.
_ENDPOINT_SCOPE_RULES = (
    ("/query", None, SCOPE_QUERY),
    ("/evaluate", None, SCOPE_EVALUATE),
    ("/configurations/endpoint_upload_destination", None, SCOPE_DEPLOY),
    ("/endpoints", _MUTATING_METHODS, SCOPE_DEPLOY),
)

# Derive advertised scopes from the enforced rules while preserving rule order.
WELL_KNOWN_ENDPOINT_SCOPES = tuple(
    dict.fromkeys(scope for _, _, scope in _ENDPOINT_SCOPE_RULES)
)


def token_has_scope(claims: dict, scope: str) -> bool:
    """True if `scope` is present in the token's space-separated `scope` claim."""
    granted = claims.get("scope", "")
    if not isinstance(granted, str):
        return False
    return scope in granted.split()


def endpoint_scope_for_path(
    path: str, subdirectory: str = "", method: str = "GET"
) -> str | None:
    """
    Return the well-known scope required for `path` + HTTP `method`, or None.

    `subdirectory` is TabPy's optional URL prefix (e.g. `/tabpy`).
    OPTIONS is not mapped here; callers skip CORS preflight separately.
    """
    rel = path or "/"
    if subdirectory:
        prefix = subdirectory if subdirectory.startswith("/") else f"/{subdirectory}"
        prefix = prefix.rstrip("/")
        if rel == prefix:
            rel = "/"
        elif rel.startswith(prefix + "/"):
            rel = rel[len(prefix):]
    verb = (method or "GET").upper()
    for path_prefix, methods, scope in _ENDPOINT_SCOPE_RULES:
        if rel == path_prefix or rel.startswith(path_prefix + "/"):
            if methods is None or verb in methods:
                return scope
    return None
