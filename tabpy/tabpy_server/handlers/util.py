import binascii
from hashlib import pbkdf2_hmac
from enum import Enum, auto


class AuthErrorStates(Enum):
    NONE = auto()
    NotAuthorized = auto()
    NotRequired = auto()


def hash_password(username, pwd):
    """
    Hashes password using PKDBF2 method:
    hash = PKDBF2('sha512', pwd, salt=username, 10000)

    Parameters
    ----------
    username : str
        User name (login). Used as salt for hashing.
        User name is lowercased befor being used in hashing.
        Salt is formatted as '_$salt@tabpy:<username>$_' to
        guarantee there's at least 16 characters.

    pwd : str
        Password to hash.

    Returns
    -------
    str
        Sting representation (hexidecimal) for PBKDF2 hash
        for the password.
    """
    salt = f"_$salt@tabpy:{username.lower()}$_"

    hash = pbkdf2_hmac(
        hash_name="sha512", password=pwd.encode(), salt=salt.encode(), iterations=10000
    )
    return binascii.hexlify(hash).decode()


def get_flight_authorization_header(headers):
    """
    Returns the Authorization value from pyarrow Flight headers.

    Header names are matched case-insensitively. A missing or empty value
    returns None so callers fail closed, as does a request carrying two
    different Authorization values: which one wins would otherwise decide
    the identity. Repeating the same value is harmless and accepted,
    since some clients set the header through more than one mechanism.
    """
    values = set()
    for header, header_values in headers.items():
        if header.lower() == "authorization":
            if isinstance(header_values, (list, tuple)):
                values.update(header_values)
            else:
                values.add(header_values)

    if len(values) != 1:
        return None
    value = values.pop()
    return value or None
