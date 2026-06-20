from app.core.config import settings


def email_domain_allowed(email: str) -> bool:
    """True if the email's domain is one of the allowed domains (or a subdomain).

    With the default config this accepts `diu.edu.bd` and any `*.diu.edu.bd`
    (e.g. `s.diu.edu.bd`) and rejects everything else (gmail, yahoo, …).
    An empty allow-list disables the restriction.
    """
    if not settings.allowed_email_domains:
        return True
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return any(
        domain == allowed or domain.endswith(f".{allowed}")
        for allowed in settings.allowed_email_domains
    )
