use crate::config::{AppConfig, AppSettings, ProjectEntry};
use crate::menu;
use serde::Serialize;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;
use tauri::{AppHandle, Manager, State, Url};

const WINDOWS_RESERVED_PROJECT_NAMES: &[&str] = &[
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
    "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
];

/// Shared state for the app configuration
pub struct ConfigState {
    pub config: Mutex<AppConfig>,
}

impl ConfigState {
    pub fn new() -> Self {
        let config = AppConfig::load().unwrap_or_default();
        Self {
            config: Mutex::new(config),
        }
    }
}

#[derive(Debug, Serialize)]
pub struct RecentProjectStatus {
    pub path: String,
    pub valid: bool,
}

fn create_project_scaffold(project_path: &PathBuf, name: &str) -> Result<(), String> {
    // Create base directory structure
    fs::create_dir_all(project_path)
        .map_err(|e| format!("Failed to create project directory: {}", e))?;

    // Create directories expected by the desktop onboarding flow.
    for subdir in [
        "db",
        "config",
        "imports",
        "logs",
        "exports/web",
        "exports/api",
    ] {
        fs::create_dir_all(project_path.join(subdir))
            .map_err(|e| format!("Failed to create {} directory: {}", subdir, e))?;
    }

    // Create minimal config.yml
    let config_content = format!(
        r#"# Niamoto Project Configuration
project:
  name: "{}"
  created_at: "{}"

database:
  path: db/niamoto.duckdb

logs:
  path: logs

exports:
  web: exports/web
  api: exports/api
"#,
        name,
        chrono::Utc::now().to_rfc3339()
    );

    fs::write(project_path.join("config/config.yml"), config_content)
        .map_err(|e| format!("Failed to create config.yml: {}", e))?;

    // Create empty import.yml, transform.yml, export.yml
    for config_file in ["import.yml", "transform.yml", "export.yml"] {
        fs::write(
            project_path.join("config").join(config_file),
            format!("# {} configuration\n", config_file.replace(".yml", "")),
        )
        .map_err(|e| format!("Failed to create {}: {}", config_file, e))?;
    }

    Ok(())
}

fn validate_project_name(name: &str) -> Result<String, String> {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return Err("Project name cannot be empty".to_string());
    }

    if trimmed != name {
        return Err("Project name cannot start or end with whitespace".to_string());
    }

    if trimmed == "." || trimmed == ".." {
        return Err("Project name is invalid".to_string());
    }

    if trimmed.ends_with('.') || trimmed.ends_with(' ') {
        return Err("Project name cannot end with a dot or space".to_string());
    }

    if trimmed.chars().any(|ch| {
        ch.is_control() || matches!(ch, '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*')
    }) {
        return Err(
            "Project name contains unsupported characters (< > : \" / \\ | ? *)".to_string(),
        );
    }

    let windows_stem = trimmed
        .split('.')
        .next()
        .unwrap_or(trimmed)
        .to_ascii_uppercase();
    if WINDOWS_RESERVED_PROJECT_NAMES.contains(&windows_stem.as_str()) {
        return Err(format!(
            "Project name '{trimmed}' is reserved on Windows and cannot be used"
        ));
    }

    Ok(trimmed.to_string())
}

/// Get the current project path
#[tauri::command]
pub fn get_current_project(state: State<ConfigState>) -> Result<Option<String>, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.get_current_project_str())
}

/// Get the list of recent projects
#[tauri::command]
pub fn get_recent_projects(state: State<ConfigState>) -> Result<Vec<ProjectEntry>, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.recent_projects.clone())
}

/// Set the current project
#[tauri::command]
pub fn set_current_project(
    app: AppHandle,
    path: String,
    state: State<ConfigState>,
) -> Result<(), String> {
    let project_path = PathBuf::from(&path);

    // Validate first
    AppConfig::validate_project_path(&project_path)?;

    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.set_current_project(project_path)?;
    drop(config);
    menu::refresh_app_menu(&app)?;

    Ok(())
}

/// Remove a project from recent projects
#[tauri::command]
pub fn remove_recent_project(
    app: AppHandle,
    path: String,
    state: State<ConfigState>,
) -> Result<(), String> {
    let project_path = PathBuf::from(&path);

    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.remove_recent_project(&project_path)?;
    drop(config);
    menu::refresh_app_menu(&app)?;

    Ok(())
}

/// Browse for a project folder using native file dialog
#[tauri::command]
pub async fn browse_project_folder(app: tauri::AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;

    // Open folder picker dialog
    let folder = app
        .dialog()
        .file()
        .set_title("Select Niamoto Project Folder")
        .blocking_pick_folder();

    match folder {
        Some(file_path) => {
            // Convert FilePath to PathBuf
            let path = file_path
                .into_path()
                .map_err(|e| format!("Failed to convert path: {}", e))?;
            let path_str = path.to_string_lossy().to_string();

            // Validate the selected folder
            match AppConfig::validate_project_path(&path) {
                Ok(_) => Ok(Some(path_str)),
                Err(e) => Err(e),
            }
        }
        None => Ok(None), // User cancelled
    }
}

/// Validate all recent projects and return their validity status
#[tauri::command]
pub fn validate_recent_projects(
    state: State<ConfigState>,
) -> Result<Vec<RecentProjectStatus>, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;

    Ok(config
        .recent_projects
        .iter()
        .map(|project| RecentProjectStatus {
            path: project.path.to_string_lossy().to_string(),
            valid: AppConfig::validate_project_path(&project.path).is_ok(),
        })
        .collect())
}

/// Validate if a path is a valid Niamoto project
#[tauri::command]
pub fn validate_project(path: String) -> Result<bool, String> {
    let project_path = PathBuf::from(&path);
    match AppConfig::validate_project_path(&project_path) {
        Ok(_) => Ok(true),
        Err(e) => Err(e),
    }
}

/// Get the NIAMOTO_HOME environment variable value for the current project
#[tauri::command]
pub fn get_niamoto_home(state: State<ConfigState>) -> Result<Option<String>, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.get_current_project_str())
}

/// Get application settings
#[tauri::command]
pub fn get_app_settings(state: State<ConfigState>) -> Result<AppSettings, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.get_settings())
}

/// Update application settings
#[tauri::command]
pub fn set_app_settings(
    app: AppHandle,
    settings: AppSettings,
    state: State<ConfigState>,
) -> Result<(), String> {
    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.set_settings(settings)?;
    drop(config);
    menu::refresh_app_menu(&app)?;
    Ok(())
}

/// Open desktop devtools on demand when debug mode is enabled
#[tauri::command]
pub fn open_desktop_devtools(app: AppHandle, state: State<ConfigState>) -> Result<(), String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    if !cfg!(debug_assertions) && !config.debug_mode {
        return Err("Desktop debug mode is disabled".to_string());
    }
    drop(config);

    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "Main window not found".to_string())?;

    window.open_devtools();
    Ok(())
}

/// Create a new Niamoto project with the standard directory structure
#[tauri::command]
pub fn create_project(
    app: AppHandle,
    name: String,
    location: String,
    state: State<ConfigState>,
) -> Result<String, String> {
    let validated_name = validate_project_name(&name)?;
    let location_path = PathBuf::from(&location);
    let project_path = location_path.join(&validated_name);

    // Validate the target doesn't already exist
    if project_path.exists() {
        return Err(format!(
            "Directory already exists: {}",
            project_path.display()
        ));
    }

    // Validate the parent directory exists
    if !location_path.exists() {
        return Err(format!(
            "Parent directory does not exist: {}",
            location_path.display()
        ));
    }

    create_project_scaffold(&project_path, &validated_name)?;

    // Set as current project
    let path_str = project_path.to_string_lossy().to_string();
    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.set_current_project(project_path)?;
    drop(config);
    menu::refresh_app_menu(&app)?;

    Ok(path_str)
}

/// Browse for a folder (for selecting project location)
#[tauri::command]
pub async fn browse_folder(app: tauri::AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;

    // Open folder picker dialog
    let folder = app
        .dialog()
        .file()
        .set_title("Select Location")
        .blocking_pick_folder();

    match folder {
        Some(file_path) => {
            let path = file_path
                .into_path()
                .map_err(|e| format!("Failed to convert path: {}", e))?;
            Ok(Some(path.to_string_lossy().to_string()))
        }
        None => Ok(None), // User cancelled
    }
}

fn validate_external_url(url: &str) -> Result<Url, String> {
    let trimmed_url = url.trim();
    if trimmed_url.is_empty() {
        return Err("URL cannot be empty".to_string());
    }

    let parsed = Url::parse(trimmed_url).map_err(|err| format!("Invalid external URL: {err}"))?;

    match parsed.scheme() {
        "https" | "http" | "mailto" => Ok(parsed),
        scheme => Err(format!(
            "Unsupported URL scheme: {scheme}. Only http, https, and mailto are allowed."
        )),
    }
}

#[tauri::command]
pub fn open_external_url(url: String) -> Result<(), String> {
    let validated_url = validate_external_url(&url)?;
    let url_str = validated_url.as_str();

    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg(url_str);
        command
    };

    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("rundll32");
        command.args(["url.dll,FileProtocolHandler", url_str]);
        command
    };

    #[cfg(all(unix, not(target_os = "macos")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(url_str);
        command
    };

    command
        .spawn()
        .map(|_| ())
        .map_err(|err| format!("Failed to open external URL: {err}"))
}

#[cfg(test)]
mod tests {
    use super::{create_project_scaffold, validate_external_url, validate_project_name};
    use std::path::PathBuf;

    fn unique_temp_project_path(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "niamoto-desktop-test-{}-{}",
            std::process::id(),
            name
        ))
    }

    #[test]
    fn create_project_scaffold_creates_expected_layout() {
        let project_path = unique_temp_project_path("scaffold");
        if project_path.exists() {
            std::fs::remove_dir_all(&project_path).unwrap();
        }

        create_project_scaffold(&project_path, "demo-project").unwrap();

        for relative_path in [
            "db",
            "config",
            "config/config.yml",
            "config/import.yml",
            "config/transform.yml",
            "config/export.yml",
            "imports",
            "logs",
            "exports/web",
            "exports/api",
        ] {
            assert!(
                project_path.join(relative_path).exists(),
                "missing {}",
                relative_path
            );
        }

        let config_content =
            std::fs::read_to_string(project_path.join("config/config.yml")).unwrap();
        assert!(config_content.contains("name: \"demo-project\""));
        assert!(config_content.contains("web: exports/web"));
        assert!(config_content.contains("api: exports/api"));

        std::fs::remove_dir_all(&project_path).unwrap();
    }

    #[test]
    fn validate_external_url_accepts_supported_schemes() {
        for url in [
            "https://niamoto.io/docs",
            "http://127.0.0.1:8080/preview",
            "mailto:support@niamoto.io",
        ] {
            assert!(
                validate_external_url(url).is_ok(),
                "expected {url} to be allowed"
            );
        }
    }

    #[test]
    fn validate_external_url_rejects_unsupported_schemes() {
        for url in [
            "",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///tmp/secret.txt",
            "ftp://example.com/archive.zip",
        ] {
            assert!(
                validate_external_url(url).is_err(),
                "expected {url} to be rejected"
            );
        }
    }

    #[test]
    fn validate_project_name_accepts_cross_platform_names() {
        for name in ["niamoto-demo", "Project 2026", "subset.v2", "Forêt"] {
            assert!(
                validate_project_name(name).is_ok(),
                "expected {name} to be accepted"
            );
        }
    }

    #[test]
    fn validate_project_name_rejects_windows_and_path_edge_cases() {
        for name in [
            "",
            "   ",
            ".",
            "..",
            "bad/name",
            "bad\\name",
            "bad:name",
            "CON",
            "nul.txt",
            "project.",
            "project ",
        ] {
            assert!(
                validate_project_name(name).is_err(),
                "expected {name} to be rejected"
            );
        }
    }
}
