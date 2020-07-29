import binascii
from hashlib import pbkdf2_hmac


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
