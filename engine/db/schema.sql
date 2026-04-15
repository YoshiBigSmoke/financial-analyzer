-- ============================================================
-- Financial Analyzer — Esquema DuckDB
-- ============================================================

-- ------------------------------------------------------------
-- Empresas
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    ticker          VARCHAR PRIMARY KEY,
    name            VARCHAR NOT NULL,
    sector          VARCHAR,
    industry        VARCHAR,
    country         VARCHAR,
    exchange        VARCHAR,
    currency        VARCHAR DEFAULT 'USD',
    market_cap      DOUBLE,
    description     TEXT,
    updated_at      TIMESTAMP DEFAULT current_timestamp
);

-- ------------------------------------------------------------
-- Precios históricos OHLCV
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prices (
    ticker          VARCHAR  NOT NULL,
    date            DATE     NOT NULL,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    adj_close       DOUBLE,
    volume          BIGINT,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Estado de resultados (Income Statement)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS income_statement (
    ticker                  VARCHAR  NOT NULL,
    period_end              DATE     NOT NULL,
    period_type             VARCHAR  NOT NULL CHECK (period_type IN ('annual', 'quarterly')),
    revenue                 DOUBLE,
    gross_profit            DOUBLE,
    operating_income        DOUBLE,
    net_income              DOUBLE,
    ebitda                  DOUBLE,
    eps_basic               DOUBLE,
    eps_diluted             DOUBLE,
    shares_outstanding      BIGINT,
    updated_at              TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (ticker, period_end, period_type),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Balance General (Balance Sheet)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS balance_sheet (
    ticker                  VARCHAR  NOT NULL,
    period_end              DATE     NOT NULL,
    period_type             VARCHAR  NOT NULL CHECK (period_type IN ('annual', 'quarterly')),
    total_assets            DOUBLE,
    total_liabilities       DOUBLE,
    total_equity            DOUBLE,
    cash_and_equivalents    DOUBLE,
    total_debt              DOUBLE,
    long_term_debt          DOUBLE,
    current_assets          DOUBLE,
    current_liabilities     DOUBLE,
    updated_at              TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (ticker, period_end, period_type),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Flujo de Caja (Cash Flow Statement)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cash_flow (
    ticker                  VARCHAR  NOT NULL,
    period_end              DATE     NOT NULL,
    period_type             VARCHAR  NOT NULL CHECK (period_type IN ('annual', 'quarterly')),
    operating_cash_flow     DOUBLE,
    investing_cash_flow     DOUBLE,
    financing_cash_flow     DOUBLE,
    free_cash_flow          DOUBLE,
    capex                   DOUBLE,
    dividends_paid          DOUBLE,
    updated_at              TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (ticker, period_end, period_type),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Ratios Financieros
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial_ratios (
    ticker                  VARCHAR  NOT NULL,
    period_end              DATE     NOT NULL,
    period_type             VARCHAR  NOT NULL CHECK (period_type IN ('annual', 'quarterly')),
    -- Valuación
    pe_ratio                DOUBLE,
    pb_ratio                DOUBLE,
    ps_ratio                DOUBLE,
    ev_ebitda               DOUBLE,
    -- Rentabilidad
    roe                     DOUBLE,
    roa                     DOUBLE,
    gross_margin            DOUBLE,
    operating_margin        DOUBLE,
    net_margin              DOUBLE,
    -- Deuda
    debt_to_equity          DOUBLE,
    current_ratio           DOUBLE,
    quick_ratio             DOUBLE,
    updated_at              TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (ticker, period_end, period_type),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Valor Intrínseco (resultados de valuaciones)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS intrinsic_value (
    id                      INTEGER PRIMARY KEY,
    ticker                  VARCHAR  NOT NULL,
    calculated_at           TIMESTAMP DEFAULT current_timestamp,
    model_type              VARCHAR  NOT NULL, -- 'DCF', 'Graham', 'DDM', etc.
    intrinsic_value         DOUBLE,
    current_price           DOUBLE,
    margin_of_safety        DOUBLE,  -- % de descuento sobre valor intrínseco
    assumptions             JSON,    -- parámetros usados en el cálculo
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Watchlist del usuario
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS watchlist (
    ticker                  VARCHAR  PRIMARY KEY,
    added_at                TIMESTAMP DEFAULT current_timestamp,
    notes                   TEXT,
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

-- ------------------------------------------------------------
-- Secuencia para intrinsic_value.id
-- ------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS seq_intrinsic_value START 1;
ALTER TABLE intrinsic_value ALTER COLUMN id SET DEFAULT nextval('seq_intrinsic_value');
