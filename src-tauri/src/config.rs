use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

pub const DESKTOP_CONFIG_ENV: &str = "NIAMOTO_DESKTOP_CONFIG";
pub const DESKTOP_LOG_DIR_ENV: &str = "NIAMOTO_DESKTOP_LOG_DIR";
const APP_IDENTIFIER: &str = "com.niamoto.desktop";

/// Desktop application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Currently selected Niamoto project path
    pub current_project: Option<PathBuf>,

    /// List of recently opened projects
    pub recent_projects: Vec<ProjectEntry>,

    /// Last updated timestamp (ISO 8601 format)
    pub last_updated: String,

    /// Whether to auto-load the last project on startup
    #[serde(default = "default_auto_load")]
    pub auto_load_last_project: bool,

    /// Preferred UI language for the desktop app
    #[serde(default = "default_ui_language")]
    pub ui_language: UiLanguagePreference,

    /// Whether desktop debug tools are enabled for on-demand troubleshooting
    #[serde(default = "default_debug_mode")]
    pub debug_mode: bool,

    /// Per-project native desktop context that must survive backend port changes.
    #[serde(default)]
    pub project_contexts: HashMap<String, ProjectDesktopContext>,
}

/// Default value for auto_load_last_project
fn default_auto_load() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum UiLanguagePreference {
    Auto,
    Fr,
    En,
}

fn default_ui_language() -> UiLanguagePreference {
    UiLanguagePreference::Auto
}

fn default_debug_mode() -> bool {
    false
}

/// Application settings exposed to the frontend
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub auto_load_last_project: bool,
    #[serde(default = "default_ui_language")]
    pub ui_language: UiLanguagePreference,
    #[serde(default = "default_debug_mode")]
    pub debug_mode: bool,
}

/// Entry for a recent project
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProjectEntry {
    /// Absolute path to the project directory
    pub path: PathBuf,

    /// Display name (usually the directory name)
    pub name: String,

    /// Last accessed timestamp (ISO 8601 format)
    pub last_accessed: String,
}

/// Restorable desktop route for a project.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ProjectDesktopRoute {
    pub pathname: String,
    pub search: String,
    pub hash: String,
}

/// Native desktop context persisted per project.
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ProjectDesktopContext {
    #[serde(default)]
    pub last_route: Option<ProjectDesktopRoute>,
    #[serde(default)]
    pub view_preferences: HashMap<String, String>,
    #[serde(default)]
    pub updated_at: Option<i64>,
}

fn is_safe_project_context_key(value: &str) -> bool {
    value.starts_with("desktop:") && value.len() <= 1024 && !value.chars().any(|ch| ch.is_control())
}

fn is_safe_route_segment(value: &str, prefix: char) -> bool {
    value.is_empty()
        || (value.starts_with(prefix)
            && value.len() <= 512
            && !value.chars().any(|ch| matches!(ch, '\r' | '\n')))
}

fn normalize_project_desktop_route(route: ProjectDesktopRoute) -> Option<ProjectDesktopRoute> {
    if !route.pathname.starts_with('/')
        || route.pathname.starts_with("//")
        || route.pathname.len() > 512
        || route
            .pathname
            .chars()
            .any(|ch| matches!(ch, '\r' | '\n' | '?' | '#'))
        || !is_safe_route_segment(&route.search, '?')
        || !is_safe_route_segment(&route.hash, '#')
    {
        return None;
    }

    Some(route)
}

fn is_safe_preference_key(value: &str) -> bool {
    let mut chars = value.chars();
    let Some(first) = chars.next() else {
        return false;
    };

    (first.is_ascii_alphabetic())
        && value.len() <= 80
        && chars.all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | ':' | '-'))
}

fn is_safe_preference_value(value: &str) -> bool {
    !value.is_empty() && value.len() <= 80 && !value.chars().any(|ch| matches!(ch, '\r' | '\n'))
}

impl ProjectDesktopContext {
    fn sanitized(self) -> Self {
        let view_preferences = self
            .view_preferences
            .into_iter()
            .filter(|(key, value)| is_safe_preference_key(key) && is_safe_preference_value(value))
            .collect();

        Self {
            last_route: self.last_route.and_then(normalize_project_desktop_route),
            view_preferences,
            updated_at: self.updated_at.filter(|value| *value > 0),
        }
    }

    fn is_empty(&self) -> bool {
        self.last_route.is_none() && self.view_preferences.is_empty()
    }
}

impl AppConfig {
    fn legacy_config_path() -> Option<PathBuf> {
        dirs::home_dir().map(|home| home.join(".niamoto").join("desktop-config.json"))
    }

    fn ensure_parent_dir(path: &Path) -> Result<(), String> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create desktop config directory: {}", e))?;
        }
        Ok(())
    }

    /// Get the path to the desktop config file using the native platform config directory.
    pub(crate) fn config_path() -> Result<PathBuf, String> {
        if let Some(config_path) = env::var_os(DESKTOP_CONFIG_ENV).map(PathBuf::from) {
            Self::ensure_parent_dir(&config_path)?;
            return Ok(config_path);
        }

        let config_path = dirs::config_dir()
            .ok_or_else(|| "Could not determine native config directory".to_string())?
            .join(APP_IDENTIFIER)
            .join("desktop-config.json");

        if config_path.exists() {
            return Ok(config_path);
        }

        if let Some(legacy_path) = Self::legacy_config_path() {
            if legacy_path.exists() {
                Self::ensure_parent_dir(&config_path)?;
                fs::copy(&legacy_path, &config_path).map_err(|e| {
                    format!(
                        "Failed to migrate desktop config from {}: {}",
                        legacy_path.display(),
                        e
                    )
                })?;
                return Ok(config_path);
            }
        }

        Self::ensure_parent_dir(&config_path)?;
        Ok(config_path)
    }

    pub fn desktop_log_dir() -> PathBuf {
        if let Some(log_dir) = env::var_os(DESKTOP_LOG_DIR_ENV).map(PathBuf::from) {
            let _ = fs::create_dir_all(&log_dir);
            return log_dir;
        }

        let log_dir = dirs::data_local_dir()
            .or_else(dirs::data_dir)
            .unwrap_or_else(std::env::temp_dir)
            .join(APP_IDENTIFIER)
            .join("logs");
        let _ = fs::create_dir_all(&log_dir);
        log_dir
    }

    /// Load the configuration from disk, creating default if not exists
    pub fn load() -> Result<Self, String> {
        let config_path = Self::config_path()?;

        if !config_path.exists() {
            // Create a default configuration
            let default_config = Self::default();
            default_config.save()?;
            return Ok(default_config);
        }

        let contents = fs::read_to_string(&config_path)
            .map_err(|e| format!("Failed to read config file: {}", e))?;

        let config: AppConfig = serde_json::from_str(&contents)
            .map_err(|e| format!("Failed to parse config file: {}", e))?;

        Ok(config)
    }

    /// Save the configuration to disk
    pub fn save(&self) -> Result<(), String> {
        let config_path = Self::config_path()?;

        let json = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Failed to serialize config: {}", e))?;

        fs::write(&config_path, json).map_err(|e| format!("Failed to write config file: {}", e))?;

        Ok(())
    }

    /// Set the current project and update recent projects list
    pub fn set_current_project(&mut self, path: PathBuf) -> Result<(), String> {
        // Validate that the path exists and is a Niamoto project
        Self::validate_project_path(&path)?;

        let name = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("Unknown")
            .to_string();

        let now = chrono::Utc::now().to_rfc3339();

        // Create project entry
        let entry = ProjectEntry {
            path: path.clone(),
            name,
            last_accessed: now.clone(),
        };

        // Update current project
        self.current_project = Some(path);

        // Update recent projects list
        // Remove if already exists
        self.recent_projects.retain(|p| p.path != entry.path);

        // Add to front of list
        self.recent_projects.insert(0, entry);

        // Keep only last 10 projects
        self.recent_projects.truncate(10);

        // Update timestamp
        self.last_updated = now;

        // Save immediately
        self.save()?;

        Ok(())
    }

    /// Remove a project from recent projects
    pub fn remove_recent_project(&mut self, path: &Path) -> Result<(), String> {
        self.recent_projects.retain(|p| p.path != path);

        // If we removed the current project, clear it
        if let Some(current) = &self.current_project {
            if current == path {
                self.current_project = None;
            }
        }

        self.last_updated = chrono::Utc::now().to_rfc3339();
        self.save()?;

        Ok(())
    }

    /// Validate that a path is a valid Niamoto project
    /// A valid project has:
    /// - A db/ directory
    /// - A config.yml file (or at minimum, the directory structure)
    pub fn validate_project_path(path: &Path) -> Result<(), String> {
        if !path.exists() {
            return Err(format!("Path does not exist: {:?}", path));
        }

        if !path.is_dir() {
            return Err(format!("Path is not a directory: {:?}", path));
        }

        // Check for db directory (main indicator of a Niamoto project)
        let db_dir = path.join("db");
        if !db_dir.is_dir() {
            return Err(format!(
                "Not a valid Niamoto project: missing 'db' directory in {:?}",
                path
            ));
        }

        let config_dir = path.join("config");
        if !config_dir.is_dir() {
            return Err(format!(
                "Not a valid Niamoto project: missing 'config' directory in {:?}",
                path
            ));
        }

        let config_file = config_dir.join("config.yml");
        if !config_file.is_file() {
            return Err(format!(
                "Not a valid Niamoto project: missing 'config/config.yml' in {:?}",
                path
            ));
        }

        Ok(())
    }

    /// Get the current project path as a string
    pub fn get_current_project_str(&self) -> Option<String> {
        self.current_project
            .as_ref()
            .and_then(|p| p.to_str())
            .map(|s| s.to_string())
    }

    pub fn get_project_desktop_context(&self, project_scope: &str) -> ProjectDesktopContext {
        self.project_contexts
            .get(project_scope)
            .cloned()
            .unwrap_or_default()
            .sanitized()
    }

    pub fn set_project_desktop_context(
        &mut self,
        project_scope: String,
        context: ProjectDesktopContext,
    ) -> Result<(), String> {
        if !is_safe_project_context_key(&project_scope) {
            return Err("Invalid project desktop context scope".to_string());
        }

        let context = context.sanitized();
        if context.is_empty() {
            self.project_contexts.remove(&project_scope);
        } else {
            self.project_contexts.insert(project_scope, context);
        }

        self.last_updated = chrono::Utc::now().to_rfc3339();
        self.save()
    }

    pub fn set_project_desktop_route(
        &mut self,
        project_scope: String,
        route: ProjectDesktopRoute,
    ) -> Result<(), String> {
        let mut context = self.get_project_desktop_context(&project_scope);
        context.last_route = normalize_project_desktop_route(route);
        context.updated_at = Some(chrono::Utc::now().timestamp_millis());
        self.set_project_desktop_context(project_scope, context)
    }
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            current_project: None,
            recent_projects: Vec::new(),
            last_updated: chrono::Utc::now().to_rfc3339(),
            auto_load_last_project: true,
            ui_language: UiLanguagePreference::Auto,
            debug_mode: false,
            project_contexts: HashMap::new(),
        }
    }
}

impl AppConfig {
    /// Get the application settings
    pub fn get_settings(&self) -> AppSettings {
        AppSettings {
            auto_load_last_project: self.auto_load_last_project,
            ui_language: self.ui_language.clone(),
            debug_mode: self.debug_mode,
        }
    }

    /// Update the application settings
    pub fn set_settings(&mut self, settings: AppSettings) -> Result<(), String> {
        self.auto_load_last_project = settings.auto_load_last_project;
        self.ui_language = settings.ui_language;
        self.debug_mode = settings.debug_mode;
        self.last_updated = chrono::Utc::now().to_rfc3339();
        self.save()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    static TEST_ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn test_default_config() {
        let config = AppConfig::default();
        assert!(config.current_project.is_none());
        assert!(config.recent_projects.is_empty());
        assert_eq!(config.ui_language, UiLanguagePreference::Auto);
        assert!(!config.debug_mode);
    }

    #[test]
    fn test_validate_project_path() {
        // Should fail for non-existent path
        let result = AppConfig::validate_project_path(Path::new("/non/existent/path"));
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_project_path_requires_config_structure() {
        let project_path =
            std::env::temp_dir().join(format!("niamoto-config-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&project_path);
        fs::create_dir_all(project_path.join("db")).unwrap();

        let missing_config = AppConfig::validate_project_path(&project_path);
        assert!(missing_config.is_err());

        fs::create_dir_all(project_path.join("config")).unwrap();
        let missing_config_file = AppConfig::validate_project_path(&project_path);
        assert!(missing_config_file.is_err());

        fs::write(
            project_path.join("config").join("config.yml"),
            "project: {}\n",
        )
        .unwrap();
        let valid = AppConfig::validate_project_path(&project_path);
        assert!(valid.is_ok());

        let _ = fs::remove_dir_all(&project_path);
    }

    #[test]
    fn test_config_path_prefers_env_override() {
        let _guard = TEST_ENV_LOCK.lock().unwrap();
        let config_path = std::env::temp_dir().join(format!(
            "niamoto-desktop-config-{}.json",
            std::process::id()
        ));
        let _ = fs::remove_file(&config_path);

        env::set_var(DESKTOP_CONFIG_ENV, &config_path);
        let resolved = AppConfig::config_path().unwrap();
        env::remove_var(DESKTOP_CONFIG_ENV);

        assert_eq!(resolved, config_path);
    }

    #[test]
    fn test_project_desktop_route_is_persisted_per_scope() {
        let _guard = TEST_ENV_LOCK.lock().unwrap();
        let config_path = std::env::temp_dir().join(format!(
            "niamoto-desktop-context-{}.json",
            std::process::id()
        ));
        let _ = fs::remove_file(&config_path);
        env::set_var(DESKTOP_CONFIG_ENV, &config_path);

        let mut config = AppConfig::default();
        config
            .set_project_desktop_route(
                "desktop:/tmp/project-a".to_string(),
                ProjectDesktopRoute {
                    pathname: "/groups/plots".to_string(),
                    search: "?tab=index".to_string(),
                    hash: "".to_string(),
                },
            )
            .unwrap();

        let reloaded = AppConfig::load().unwrap();
        assert_eq!(
            reloaded
                .get_project_desktop_context("desktop:/tmp/project-a")
                .last_route,
            Some(ProjectDesktopRoute {
                pathname: "/groups/plots".to_string(),
                search: "?tab=index".to_string(),
                hash: "".to_string(),
            })
        );
        assert_eq!(
            reloaded
                .get_project_desktop_context("desktop:/tmp/project-b")
                .last_route,
            None
        );

        env::remove_var(DESKTOP_CONFIG_ENV);
        let _ = fs::remove_file(&config_path);
    }

    #[test]
    fn test_project_desktop_context_rejects_invalid_scope_and_route() {
        let _guard = TEST_ENV_LOCK.lock().unwrap();
        let config_path = std::env::temp_dir().join(format!(
            "niamoto-desktop-context-invalid-{}.json",
            std::process::id()
        ));
        let _ = fs::remove_file(&config_path);
        env::set_var(DESKTOP_CONFIG_ENV, &config_path);

        let mut config = AppConfig::default();
        let invalid_scope = config.set_project_desktop_route(
            "project:Demo:unknown".to_string(),
            ProjectDesktopRoute {
                pathname: "/publish".to_string(),
                search: "".to_string(),
                hash: "".to_string(),
            },
        );
        assert!(invalid_scope.is_err());

        config
            .set_project_desktop_route(
                "desktop:/tmp/project-a".to_string(),
                ProjectDesktopRoute {
                    pathname: "/publish?bad=true".to_string(),
                    search: "".to_string(),
                    hash: "".to_string(),
                },
            )
            .unwrap();
        assert!(!config
            .project_contexts
            .contains_key("desktop:/tmp/project-a"));

        env::remove_var(DESKTOP_CONFIG_ENV);
        let _ = fs::remove_file(&config_path);
    }
}
