fn main() {
    forward_feedback_env(
        "NIAMOTO_FEEDBACK_WORKER_URL",
        &[
            "NIAMOTO_FEEDBACK_WORKER_URL",
            "FEEDBACK_WORKER_URL",
            "VITE_FEEDBACK_WORKER_URL",
        ],
    );
    forward_feedback_env(
        "NIAMOTO_FEEDBACK_API_KEY",
        &[
            "NIAMOTO_FEEDBACK_API_KEY",
            "FEEDBACK_API_KEY",
            "VITE_FEEDBACK_API_KEY",
        ],
    );

    tauri_build::build()
}

fn forward_feedback_env(target: &str, sources: &[&str]) {
    for source in sources {
        println!("cargo:rerun-if-env-changed={source}");
    }

    if let Some(value) = sources.iter().find_map(|source| {
        std::env::var(source)
            .ok()
            .map(|value| value.trim().to_owned())
            .filter(|value| !value.is_empty())
    }) {
        println!("cargo:rustc-env={target}={value}");
    }
}
