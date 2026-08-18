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
