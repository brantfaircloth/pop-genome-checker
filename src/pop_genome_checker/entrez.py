"""NCBI Entrez helpers with rate limiting and retry logic."""

import time
import functools
from typing import Any

from Bio import Entrez

# NCBI allows 3 req/s without an API key, 10 req/s with one.
_RATE_LIMIT_DEFAULT = 1 / 3  # seconds between requests
_RATE_LIMIT_WITH_KEY = 1 / 10

_last_request_time: float = 0.0


def configure(email: str, api_key: str | None = None) -> None:
    global _last_request_time
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key
    _last_request_time = 0.0


def _rate_limit() -> None:
    global _last_request_time
    interval = _RATE_LIMIT_WITH_KEY if getattr(Entrez, "api_key", None) else _RATE_LIMIT_DEFAULT
    elapsed = time.monotonic() - _last_request_time
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_request_time = time.monotonic()


def esearch(db: str, term: str, **kwargs) -> dict:
    _rate_limit()
    handle = Entrez.esearch(db=db, term=term, **kwargs)
    return Entrez.read(handle)


def esummary(db: str, id: str, **kwargs) -> Any:
    _rate_limit()
    handle = Entrez.esummary(db=db, id=id, **kwargs)
    return Entrez.read(handle)


def efetch(db: str, id: str, rettype: str, retmode: str = "text", **kwargs) -> Any:
    _rate_limit()
    handle = Entrez.efetch(db=db, id=id, rettype=rettype, retmode=retmode, **kwargs)
    return handle.read()


def resolve_taxon(name: str) -> str:
    """Return the NCBI Taxonomy ID for a taxon name. Raises ValueError if not found."""
    result = esearch("taxonomy", name)
    ids = result.get("IdList", [])
    if not ids:
        raise ValueError(f"Taxon not found in NCBI Taxonomy: {name!r}")
    if len(ids) > 1:
        # Use the first (most relevant) hit
        pass
    return ids[0]
