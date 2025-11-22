use crate::config::{AppConfig, ProjectEntry};
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::State;

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
    path: String,
    state: State<ConfigState>,
) -> Result<(), String> {
    let project_path = PathBuf::from(&path);

    // Validate first
    AppConfig::validate_project_path(&project_path)?;

    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.set_current_project(project_path)?;

    Ok(())
}

/// Remove a project from recent projects
#[tauri::command]
pub fn remove_recent_project(
    path: String,
    state: State<ConfigState>,
) -> Result<(), String> {
    let project_path = PathBuf::from(&path);

    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.remove_recent_project(&project_path)?;

    Ok(())
}

/// Browse for a project folder using native file dialog
#[tauri::command]
pub async fn browse_project_folder(app: tauri::AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

    // Open folder picker dialog
    let folder = app.dialog()
        .file()
        .set_title("Select Niamoto Project Folder")
        .blocking_pick_folder();

    match folder {
        Some(file_path) => {
            // Convert FilePath to PathBuf
            let path = file_path.into_path().map_err(|e| format!("Failed to convert path: {}", e))?;
            let path_str = path.to_string_lossy().to_string();

            // Validate the selected folder
            match AppConfig::validate_project_path(&path) {
                Ok(_) => Ok(Some(path_str)),
                Err(e) => {
                    // Show error dialog
                    app.dialog()
                        .message(format!("Invalid Niamoto project:\n\n{}\n\nMake sure the directory contains a 'db' folder.", e))
                        .kind(MessageDialogKind::Error)
                        .title("Invalid Project")
                        .blocking_show();

                    Err(e)
                }
            }
        }
        None => Ok(None), // User cancelled
    }
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
