"""
Prueba del pipeline completo: descarga AAPL y verifica que los datos llegaron a DuckDB.
Correr desde la raíz: python -m engine.data.test_data
"""

from engine.db.connection import get_connection, close_connection
from engine.data.pipeline import load_ticker


def main():
    conn = get_connection()

    load_ticker(conn, "AAPL", period="2y")

    # Verificar precios
    prices = conn.execute("""
        SELECT date, close, volume FROM prices
        WHERE ticker = 'AAPL'
        ORDER BY date DESC LIMIT 5
    """).fetchall()
    print("Últimos precios AAPL:")
    for row in prices:
        print(" ", row)

    # Verificar income statement
    income = conn.execute("""
        SELECT period_end, period_type, revenue, net_income, eps_diluted
        FROM income_statement
        WHERE ticker = 'AAPL'
        ORDER BY period_end DESC LIMIT 4
    """).fetchall()
    print("\nIncome statement AAPL (últimos 4 períodos):")
    for row in income:
        print(" ", row)

    # Verificar balance sheet
    balance = conn.execute("""
        SELECT period_end, period_type, total_assets, total_debt, total_equity
        FROM balance_sheet
        WHERE ticker = 'AAPL'
        ORDER BY period_end DESC LIMIT 4
    """).fetchall()
    print("\nBalance sheet AAPL (últimos 4 períodos):")
    for row in balance:
        print(" ", row)

    close_connection()


if __name__ == "__main__":
    main()
