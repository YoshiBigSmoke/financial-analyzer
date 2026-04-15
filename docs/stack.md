# Financial Analyzer — Stack y estructura

## Tecnologías

| Capa | Tecnología | Rol |
|---|---|---|
| Desktop shell | Tauri (Rust) | App nativa, comunicación frontend↔engine |
| Frontend | React + TypeScript | UI de la ventana |
| Estilos | TailwindCSS | Tema oscuro |
| Gráficas | TradingView Lightweight Charts | Precios y series de tiempo |
| Tablas | AG Grid | Datos financieros |
| Motor análisis | Python | Fundamental, técnico, cuantitativo |
| DataFrames | Polars | Manipulación de datos (rápido) |
| Análisis técnico | TA-Lib | Indicadores (C internamente) |
| Modelos quant | statsmodels / PyTorch | ARIMA, GARCH, ML |
| Datos mercado | yfinance + EDGAR API | Precios y fundamentales |
| Base de datos | DuckDB | OLAP embebida |
| Almacenamiento | Parquet | Históricos de precios |

## Estructura de carpetas

```
financial-analyzer/
├── src-tauri/          ← Rust/Tauri
│   └── src/
├── src/                ← React frontend
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   └── store/
├── engine/             ← Python engine
│   ├── fundamental/
│   ├── technical/
│   ├── quant/
│   ├── data/
│   └── db/
├── data/               ← Almacenamiento local
│   ├── db/
│   └── parquet/
└── docs/
```

## Módulos (a desarrollar en orden)

1. `engine/db/` — Conexión DuckDB, esquema inicial
2. `engine/data/` — Fetchers yfinance / EDGAR
3. `engine/fundamental/` — Ratios, DCF, valor intrínseco
4. `engine/technical/` — Indicadores TA-Lib
5. `engine/quant/` — Modelos de predicción
6. `src/` — UI React (componentes, páginas)
7. `src-tauri/` — Integración Tauri (IPC, comandos)
