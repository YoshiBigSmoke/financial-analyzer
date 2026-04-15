use std::process::Command;
use std::path::PathBuf;


/// Busca el ejecutable Python: primero el venv local, luego python3/python del PATH.
fn python_bin(project_root: &PathBuf) -> PathBuf {
    let candidates = [
        project_root.join("venv/bin/python"),
        project_root.join(".venv/bin/python"),
        PathBuf::from("python3"),
        PathBuf::from("python"),
    ];
    for p in &candidates {
        if p.exists() || p.file_name().is_some() {
            // Para paths relativos como "python3" siempre los dejamos pasar
            if p.is_absolute() {
                if p.exists() {
                    return p.clone();
                }
            } else {
                return p.clone();
            }
        }
    }
    PathBuf::from("python3")
}

/// Devuelve la raíz del proyecto (donde está engine/, venv/, etc.)
fn project_root() -> PathBuf {
    // En dev: el exe está en src-tauri/target/debug/
    // Subimos hasta encontrar engine/ o usamos el directorio actual
    let mut dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));

    for _ in 0..6 {
        if dir.join("engine").is_dir() {
            return dir;
        }
        if let Some(parent) = dir.parent() {
            dir = parent.to_path_buf();
        } else {
            break;
        }
    }

    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

/// Comando IPC principal.
/// Frontend llama: invoke("run_engine", { command, args })
///   command : nombre del comando Python (ej. "fundamental")
///   args    : objeto JSON con los parámetros
#[tauri::command]
async fn run_engine(
    command: String,
    args: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let root   = project_root();
    let python = python_bin(&root);
    let args_str = serde_json::to_string(&args).map_err(|e| e.to_string())?;

    let output = Command::new(&python)
        .arg("-m")
        .arg("engine.api")
        .arg(&command)
        .arg(&args_str)
        .current_dir(&root)
        .output()
        .map_err(|e| format!("No se pudo ejecutar Python ({python:?}): {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if stdout.trim().is_empty() {
        return Err(format!("Engine sin output.\nstderr: {stderr}"));
    }

    let result: serde_json::Value = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("JSON inválido: {e}\nOutput: {stdout}\nstderr: {stderr}"))?;

    // Si el engine devolvió ok:false, propagamos como error
    if result.get("ok") == Some(&serde_json::Value::Bool(false)) {
        let msg = result["error"].as_str().unwrap_or("Error desconocido");
        return Err(msg.to_string());
    }

    Ok(result["data"].clone())
}

/// Ping para verificar que el backend Rust responde.
#[tauri::command]
fn ping() -> String {
    "pong".to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![run_engine, ping])
        .run(tauri::generate_context!())
        .expect("Error al arrancar la app");
}
