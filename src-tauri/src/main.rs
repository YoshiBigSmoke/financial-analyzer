// Evita que se abra una consola en Windows al lanzar la app
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    financial_analyzer_lib::run();
}
