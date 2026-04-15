import sys
"""
Modelo DCF (Discounted Cash Flow) para calcular valor intrínseco.

Lógica:
  1. Toma los últimos N años de Free Cash Flow
  2. Calcula la tasa de crecimiento histórica promedio
  3. Proyecta el FCF para los próximos `years` años
  4. Calcula el valor terminal con Gordon Growth Model
  5. Descuenta todo al presente con la tasa WACC
  6. Divide por shares outstanding → valor intrínseco por acción
"""

import math
import duckdb
from engine.db.queries import save_intrinsic_value


def _get_fcf_history(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    n: int = 5,
) -> list[float]:
    """
    Devuelve los últimos N años de FCF ordenados del más antiguo al más reciente.
    Filtra años con FCF None o 0.
    """
    rows = conn.execute("""
        SELECT free_cash_flow FROM cash_flow
        WHERE ticker = ? AND period_type = 'annual' AND free_cash_flow IS NOT NULL AND free_cash_flow != 0
        ORDER BY period_end DESC LIMIT ?
    """, [ticker, n]).fetchall()

    fcfs = [r[0] for r in rows]
    return list(reversed(fcfs))  # del más antiguo al más reciente


def _get_shares_outstanding(conn: duckdb.DuckDBPyConnection, ticker: str) -> float | None:
    row = conn.execute("""
        SELECT shares_outstanding FROM income_statement
        WHERE ticker = ? AND period_type = 'annual' AND shares_outstanding IS NOT NULL
        ORDER BY period_end DESC LIMIT 1
    """, [ticker]).fetchone()
    return row[0] if row else None


def _get_latest_price(conn: duckdb.DuckDBPyConnection, ticker: str) -> float | None:
    row = conn.execute("""
        SELECT adj_close FROM prices
        WHERE ticker = ? ORDER BY date DESC LIMIT 1
    """, [ticker]).fetchone()
    return row[0] if row else None


def _cagr(values: list[float]) -> float | None:
    """
    Calcula CAGR (Compound Annual Growth Rate) entre el primer y último valor.
    Devuelve None si no se puede calcular.
    """
    if len(values) < 2 or values[0] <= 0 or values[-1] <= 0:
        return None
    n = len(values) - 1
    return (values[-1] / values[0]) ** (1 / n) - 1


def run_dcf(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    discount_rate: float = 0.10,   # WACC / tasa de descuento
    terminal_growth: float = 0.03,  # crecimiento perpetuo (≈ inflación)
    years: int = 10,               # años de proyección
    growth_override: float | None = None,  # si se provee, ignora el CAGR histórico
) -> dict | None:
    """
    Ejecuta el modelo DCF y guarda el resultado en intrinsic_value.

    Parámetros:
        discount_rate    : tasa de descuento (WACC). Default 10%
        terminal_growth  : crecimiento a perpetuidad. Default 3%
        years            : años de proyección. Default 10
        growth_override  : fuerza una tasa de crecimiento específica

    Devuelve dict con el resultado, o None si faltan datos.
    """
    ticker = ticker.upper()

    fcfs = _get_fcf_history(conn, ticker, n=5)
    if not fcfs:
        print(f"[{ticker}] DCF: sin datos de FCF.", file=sys.stderr, flush=True)
        return None

    shares = _get_shares_outstanding(conn, ticker)
    if not shares or shares <= 0:
        print(f"[{ticker}] DCF: sin datos de shares outstanding.", file=sys.stderr, flush=True)
        return None

    current_price = _get_latest_price(conn, ticker)

    # Tasa de crecimiento
    if growth_override is not None:
        growth_rate = growth_override
    else:
        cagr = _cagr(fcfs)
        if cagr is None:
            print(f"[{ticker}] DCF: no se puede calcular CAGR.", file=sys.stderr, flush=True)
            return None
        # Limitamos el crecimiento para no volvernos locos con empresas en racha
        # Floor en 0%: si el FCF histórico decrece asumimos crecimiento plano,
        # no declive perpetuo (evita valuaciones irreales para empresas rentables)
        growth_rate = max(min(cagr, 0.30), 0.0)

    base_fcf = fcfs[-1]  # FCF más reciente como punto de partida

    # Proyectar FCFs y descontarlos
    pv_fcfs = 0.0
    projected = []
    for i in range(1, years + 1):
        fcf_i = base_fcf * (1 + growth_rate) ** i
        pv_i = fcf_i / (1 + discount_rate) ** i
        pv_fcfs += pv_i
        projected.append(round(fcf_i, 0))

    # Valor terminal (Gordon Growth Model)
    fcf_terminal = base_fcf * (1 + growth_rate) ** years * (1 + terminal_growth)
    terminal_value = fcf_terminal / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** years

    # Valor intrínseco total
    total_equity_value = pv_fcfs + pv_terminal
    intrinsic_per_share = total_equity_value / shares

    # Margen de seguridad
    margin_of_safety = None
    if current_price and intrinsic_per_share > 0:
        margin_of_safety = (intrinsic_per_share - current_price) / intrinsic_per_share

    result = {
        "ticker":           ticker,
        "model_type":       "DCF",
        "intrinsic_value":  round(intrinsic_per_share, 2),
        "current_price":    current_price,
        "margin_of_safety": round(margin_of_safety, 4) if margin_of_safety is not None else None,
        "assumptions": {
            "discount_rate":   discount_rate,
            "terminal_growth": terminal_growth,
            "years":           years,
            "growth_rate":     round(growth_rate, 4),
            "base_fcf":        base_fcf,
            "fcf_history":     [round(f, 0) for f in fcfs],
            "projected_fcfs":  projected,
            "pv_fcfs":         round(pv_fcfs, 0),
            "pv_terminal":     round(pv_terminal, 0),
            "shares":          shares,
        },
    }

    save_intrinsic_value(conn, result)
    return result
