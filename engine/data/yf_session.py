"""
Sesión compartida para yfinance.

Yahoo Finance necesita:
  1. Cookies de consent (de guce.yahoo.com)
  2. Un crumb de autenticación

curl_cffi con browser impersonation falla en este entorno por un bug de BoringSSL.
La solución: usar curl_cffi SIN impersonation + cookies de consent manualmente.
Esto funciona porque Yahoo acepta la autenticación básica si tienes las cookies correctas.
"""

import sys
import time

_session = None  # singleton


def get_session():
    """
    Devuelve una sesión curl_cffi lista para usar con yfinance.
    Se crea una vez y se reutiliza (singleton).
    """
    global _session
    if _session is not None:
        return _session

    try:
        import curl_cffi.requests as cr
    except ImportError:
        return None

    s = cr.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT":             "1",
        "Connection":      "keep-alive",
    })

    # Obtener cookies de consent — necesario para que el crumb funcione
    try:
        s.get("https://guce.yahoo.com/consent", timeout=10)
        print("[session] Cookies de Yahoo obtenidas.", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[session] Advertencia: no se pudieron obtener cookies: {e}", file=sys.stderr, flush=True)

    _session = s
    return _session


def reset_session():
    """Fuerza recrea la sesión (útil si expiraron las cookies)."""
    global _session
    _session = None
