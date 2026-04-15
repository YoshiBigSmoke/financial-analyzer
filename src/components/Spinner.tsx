const LOADING_TIPS = [
  "analizando los libros contables...",
  "consultando el oráculo cuantitativo...",
  "corriendo simulaciones Monte Carlo...",
  "calculando valor intrínseco...",
  "leyendo las señales del mercado...",
];

export function Spinner({ label }: { label?: string }) {
  const tip = LOADING_TIPS[Math.floor(Math.random() * LOADING_TIPS.length)];
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 16,
      flex: 1,
      padding: 40,
    }}>
      <div style={{ fontSize: 42, animation: "spin 1.2s linear infinite", display: "inline-block" }}>
        🌸
      </div>
      <div style={{
        color: "var(--lavender)",
        fontWeight: 600,
        fontSize: 14,
        textAlign: "center",
        maxWidth: 320,
      }}>
        {label ?? "Cargando..."}
      </div>
      <div style={{ color: "var(--text-muted)", fontSize: 12 }}>
        {tip}
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
