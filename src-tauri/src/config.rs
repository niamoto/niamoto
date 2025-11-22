use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

/// Desktop application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Currently selected Niamoto project path
    pub current_project: Option<PathBuf>,

    /// List of recently opened projects
    pub recent_projects: Vec<ProjectEntry>,

    /// Last updated timestamp (ISO 8601 format)
    pub last_updated: String,
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

impl AppConfig {
    /// Get the path to the desktop config file (~/.niamoto/desktop-config.json)
    fn config_path() -> Result<PathBuf, String> {
        let home = dirs::home_dir()
            .ok_or_else(|| "Could not determine home directory".to_string())?;

        let niamoto_dir = home.join(".niamoto");

        // Create the directory if it doesn't exist
        if !niamoto_dir.exists() {
            fs::create_dir_all(&niamoto_dir)
                .map_err(|e| format!("Failed to create ~/.niamoto directory: {}", e))?;
        }

        Ok(niamoto_dir.join("desktop-config.json"))
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

        fs::write(&config_path, json)
            .map_err(|e| format!("Failed to write config file: {}", e))?;

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
        if !db_dir.exists() {
            return Err(format!(
                "Not a valid Niamoto project: missing 'db' directory in {:?}",
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
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            current_project: None,
            recent_projects: Vec::new(),
            last_updated: chrono::Utc::now().to_rfc3339(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_default_config() {
        let config = AppConfig::default();
        assert!(config.current_project.is_none());
        assert!(config.recent_projects.is_empty());
    }

    #[test]
    fn test_validate_project_path() {
        // Should fail for non-existent path
        let result = AppConfig::validate_project_path(Path::new("/non/existent/path"));
        assert!(result.is_err());
    }
}
