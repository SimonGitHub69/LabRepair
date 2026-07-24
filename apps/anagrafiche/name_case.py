def format_cognome(value):
    return (value or "").strip().upper()


def format_nome(value):
    return " ".join(
        (part[:1].upper() + part[1:].lower()) if part else ""
        for part in (value or "").strip().split()
    )
