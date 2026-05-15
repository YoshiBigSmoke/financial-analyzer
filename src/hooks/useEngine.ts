import { useState, useCallback } from "react";

type Status = "idle" | "loading" | "done" | "error";

// Detecta si la app está corriendo dentro de Tauri (desktop) o en el browser (dev/preview)
const IN_TAURI = "__TAURI_INTERNALS__" in window;

export function useEngine<T = unknown>() {
  const [data,   setData]   = useState<T | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error,  setError]  = useState<string | null>(null);

  const call = useCallback(async (command: string, args: Record<string, unknown> = {}) => {
    setStatus("loading");
    setError(null);
    setData(null);
    try {
      let result: T;
      if (IN_TAURI) {
        // Modo desktop: llama al engine Python via Tauri
        const { invoke } = await import("@tauri-apps/api/core");
        result = await invoke<T>("run_engine", { command, args });
      } else {
        // Modo navegador: usa datos de prueba para ver la UI sin backend
        const { getMockData } = await import("../mock");
        await new Promise(r => setTimeout(r, 400)); // simula latencia real
        result = getMockData(command, args) as T;
      }
      setData(result);
      setStatus("done");
      return result;
    } catch (e) {
      const msg = typeof e === "string" ? e : JSON.stringify(e);
      setError(msg);
      setStatus("error");
      return null;
    }
  }, []);

  return { data, status, error, call };
}
