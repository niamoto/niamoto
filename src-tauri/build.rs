use std::collections::HashMap;
use std::path::PathBuf;

fn main() {
    let frontend_env = load_frontend_production_env();

    forward_feedback_env(
        "NIAMOTO_FEEDBACK_WORKER_URL",
        &[
            "NIAMOTO_FEEDBACK_WORKER_URL",
            "FEEDBACK_WORKER_URL",
            "VITE_FEEDBACK_WORKER_URL",
        ],
        &frontend_env,
    );
    forward_feedback_env(
        "NIAMOTO_FEEDBACK_API_KEY",
        &[
            "NIAMOTO_FEEDBACK_API_KEY",
            "FEEDBACK_API_KEY",
            "VITE_FEEDBACK_API_KEY",
        ],
        &frontend_env,
    );

    tauri_build::build()
}

fn forward_feedback_env(target: &str, sources: &[&str], frontend_env: &HashMap<String, String>) {
    for source in sources {
        println!("cargo:rerun-if-env-changed={source}");
    }

    if let Some(value) = read_configured_env_value(sources)
        .or_else(|| read_frontend_env_value(sources, frontend_env))
    {
        println!("cargo:rustc-env={target}={value}");
    }
}

fn read_configured_env_value(sources: &[&str]) -> Option<String> {
    sources.iter().find_map(|source| {
        std::env::var(source)
            .ok()
            .map(|value| value.trim().to_owned())
            .filter(|value| !value.is_empty())
    })
}

fn read_frontend_env_value(
    sources: &[&str],
    frontend_env: &HashMap<String, String>,
) -> Option<String> {
    sources.iter().find_map(|source| {
        frontend_env
            .get(*source)
            .map(|value| value.trim().to_owned())
            .filter(|value| !value.is_empty())
    })
}

fn load_frontend_production_env() -> HashMap<String, String> {
    let path = frontend_production_env_path();
    println!("cargo:rerun-if-changed={}", path.display());

    std::fs::read_to_string(path)
        .map(|content| parse_env_file(&content))
        .unwrap_or_default()
}

fn frontend_production_env_path() -> PathBuf {
    let manifest_dir =
        PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| String::from(".")));
    let project_root = manifest_dir.parent().unwrap_or(&manifest_dir);
    project_root.join("src/niamoto/gui/ui/.env.production")
}

fn parse_env_file(content: &str) -> HashMap<String, String> {
    content
        .lines()
        .filter_map(parse_env_line)
        .collect::<HashMap<_, _>>()
}

fn parse_env_line(line: &str) -> Option<(String, String)> {
    let line = line.trim();
    if line.is_empty() || line.starts_with('#') {
        return None;
    }

    let (key, value) = line.split_once('=')?;
    let key = key
        .trim()
        .strip_prefix("export ")
        .unwrap_or_else(|| key.trim())
        .trim();
    if key.is_empty() {
        return None;
    }

    let value = normalize_env_value(value);
    if value.is_empty() {
        return None;
    }

    Some((key.to_owned(), value))
}

fn normalize_env_value(value: &str) -> String {
    let value = value.trim();
    if value.len() >= 2
        && ((value.starts_with('"') && value.ends_with('"'))
            || (value.starts_with('\'') && value.ends_with('\'')))
    {
        return value[1..value.len() - 1].to_owned();
    }

    value.to_owned()
}
