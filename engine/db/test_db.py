"""
Prueba rápida: crea la DB, inserta una empresa de ejemplo y la lee.
Correr desde la raíz del proyecto: python -m engine.db.test_db
"""

from engine.db.connection import get_connection, close_connection
from engine.db.queries import upsert_company, get_company, add_to_watchlist, get_watchlist


def main():
    conn = get_connection()
    print("Conexión OK:", conn)

    # Insertar empresa de prueba
    upsert_company(conn, {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "US",
        "exchange": "NASDAQ",
        "currency": "USD",
        "market_cap": 3_000_000_000_000.0,
        "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.",
    })
    print("Empresa insertada.")

    # Leer
    company = get_company(conn, "AAPL")
    print("Empresa leída:", company)

    # Watchlist
    add_to_watchlist(conn, "AAPL", notes="Primera empresa de prueba")
    watchlist = get_watchlist(conn)
    print("Watchlist:", watchlist)

    close_connection()
    print("Todo OK.")


if __name__ == "__main__":
    main()
