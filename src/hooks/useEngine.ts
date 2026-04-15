import { useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";

type Status = "idle" | "loading" | "done" | "error";

export function useEngine<T = unknown>() {
  const [data,   setData]   = useState<T | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error,  setError]  = useState<string | null>(null);

  const call = useCallback(async (command: string, args: Record<string, unknown> = {}) => {
    setStatus("loading");
    setError(null);
    try {
      const result = await invoke<T>("run_engine", { command, args });
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
