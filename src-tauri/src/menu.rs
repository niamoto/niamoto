use crate::commands::ConfigState;
use crate::config::{AppConfig, UiLanguagePreference};
use serde::Serialize;
use std::path::Path;
use tauri::menu::{
    Menu, MenuEvent, MenuItemBuilder, PredefinedMenuItem, SubmenuBuilder, HELP_SUBMENU_ID,
    WINDOW_SUBMENU_ID,
};
use tauri::{AppHandle, Emitter, Manager, Runtime, State};
use tauri_plugin_dialog::DialogExt;

const MAIN_WINDOW_LABEL: &str = "main";

pub const DESKTOP_MENU_ACTION_EVENT: &str = "desktop://menu-action";
pub const DESKTOP_PROJECT_SELECTED_EVENT: &str = "desktop://project-selected";

const MENU_OPEN_PROJECT: &str = "file.open_project";
const MENU_OPEN_RECENT_SUBMENU: &str = "file.open_recent";
const MENU_SETTINGS: &str = "file.settings";

const MENU_COMMAND_PALETTE: &str = "view.command_palette";
const MENU_TOGGLE_SIDEBAR: &str = "view.toggle_sidebar";
const MENU_RELOAD_UI: &str = "view.reload_ui";
const MENU_TOGGLE_DEVTOOLS: &str = "view.toggle_devtools";

const MENU_DOCUMENTATION: &str = "help.documentation";
const MENU_SHORTCUTS: &str = "help.shortcuts";
const MENU_ABOUT: &str = "help.about";

const RECENT_PROJECT_ID_PREFIX: &str = "file.open_recent.";

#[derive(Clone, Serialize)]
struct FrontendMenuActionPayload<'a> {
    action: &'a str,
}

#[derive(Clone, Serialize)]
struct ProjectSelectedPayload {
    path: String,
}

#[derive(Clone, Copy)]
enum MenuLanguage {
    English,
    French,
}

struct MenuLabels {
    file: &'static str,
    open_project: &'static str,
    open_recent: &'static str,
    settings: &'static str,
    quit: Option<&'static str>,
    view: &'static str,
    command_palette: &'static str,
    toggle_sidebar: &'static str,
    reload_ui: &'static str,
    toggle_devtools: &'static str,
    window: &'static str,
    help: &'static str,
    documentation: &'static str,
    shortcuts: &'static str,
    about: &'static str,
    unavailable_suffix: &'static str,
    project_picker_title: &'static str,
}

fn current_language(config: &AppConfig) -> MenuLanguage {
    match config.ui_language {
        UiLanguagePreference::Fr => MenuLanguage::French,
        UiLanguagePreference::En => MenuLanguage::English,
        UiLanguagePreference::Auto => std::env::var("LANG")
            .ok()
            .map(|value| value.to_ascii_lowercase().starts_with("fr"))
            .unwrap_or(false)
            .then_some(MenuLanguage::French)
            .unwrap_or(MenuLanguage::English),
    }
}

fn labels_for(language: MenuLanguage) -> MenuLabels {
    match language {
        MenuLanguage::French => MenuLabels {
            file: "Fichier",
            open_project: "Ouvrir un projet...",
            open_recent: "Ouvrir récent",
            settings: "Paramètres",
            quit: Some("Quitter"),
            view: "Affichage",
            command_palette: "Palette de commande",
            toggle_sidebar: "Afficher/Masquer la barre latérale",
            reload_ui: "Recharger l’interface",
            toggle_devtools: "Ouvrir les DevTools",
            window: "Fenêtre",
            help: "Aide",
            documentation: "Documentation",
            shortcuts: "Raccourcis clavier",
            about: "À propos de Niamoto",
            unavailable_suffix: "indisponible",
            project_picker_title: "Sélectionner un dossier de projet Niamoto",
        },
        MenuLanguage::English => MenuLabels {
            file: "File",
            open_project: "Open Project...",
            open_recent: "Open Recent",
            settings: "Settings",
            quit: Some("Quit"),
            view: "View",
            command_palette: "Command Palette",
            toggle_sidebar: "Toggle Sidebar",
            reload_ui: "Reload UI",
            toggle_devtools: "Toggle DevTools",
            window: "Window",
            help: "Help",
            documentation: "Documentation",
            shortcuts: "Keyboard Shortcuts",
            about: "About Niamoto",
            unavailable_suffix: "unavailable",
            project_picker_title: "Select Niamoto Project Folder",
        },
    }
}

fn devtools_accelerator() -> &'static str {
    #[cfg(target_os = "macos")]
    {
        "Alt+Command+I"
    }

    #[cfg(not(target_os = "macos"))]
    {
        "Ctrl+Shift+I"
    }
}

fn desktop_debug_enabled(config: &AppConfig) -> bool {
    cfg!(debug_assertions) || config.debug_mode
}

fn recent_project_label(entry: &crate::config::ProjectEntry, labels: &MenuLabels) -> String {
    if AppConfig::validate_project_path(&entry.path).is_ok() {
        entry.name.clone()
    } else {
        format!("{} - {}", entry.name, labels.unavailable_suffix)
    }
}

fn emit_frontend_action<R: Runtime>(
    app: &AppHandle<R>,
    action: &'static str,
) -> Result<(), String> {
    app.emit_to(
        MAIN_WINDOW_LABEL,
        DESKTOP_MENU_ACTION_EVENT,
        FrontendMenuActionPayload { action },
    )
    .map_err(|err| err.to_string())
}

fn emit_project_selected<R: Runtime>(app: &AppHandle<R>, path: String) -> Result<(), String> {
    app.emit_to(
        MAIN_WINDOW_LABEL,
        DESKTOP_PROJECT_SELECTED_EVENT,
        ProjectSelectedPayload { path },
    )
    .map_err(|err| err.to_string())
}

fn set_current_project<R: Runtime>(app: &AppHandle<R>, path: &Path) -> Result<(), String> {
    AppConfig::validate_project_path(path)?;

    let path_buf = path.to_path_buf();
    let path_string = path_buf.to_string_lossy().to_string();
    let state: State<ConfigState> = app.state();

    {
        let mut config = state.config.lock().map_err(|err| err.to_string())?;
        config.set_current_project(path_buf)?;
    }

    refresh_app_menu(app)?;
    emit_project_selected(app, path_string)
}

fn open_project_dialog<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let config = current_config(app)?;
    let labels = labels_for(current_language(&config));
    let app_handle = app.clone();

    app.dialog()
        .file()
        .set_title(labels.project_picker_title)
        .pick_folder(move |folder| {
            let Some(file_path) = folder else {
                return;
            };

            let path = match file_path.into_path() {
                Ok(path) => path,
                Err(err) => {
                    eprintln!("Failed to convert selected path: {}", err);
                    return;
                }
            };

            if let Err(err) = set_current_project(&app_handle, &path) {
                eprintln!("Failed to open selected project from menu: {}", err);
            }
        });

    Ok(())
}

fn open_recent_project<R: Runtime>(app: &AppHandle<R>, index: usize) -> Result<(), String> {
    let state: State<ConfigState> = app.state();
    let recent_path = {
        let config = state.config.lock().map_err(|err| err.to_string())?;
        config
            .recent_projects
            .get(index)
            .map(|entry| entry.path.clone())
            .ok_or_else(|| format!("Recent project at index {index} no longer exists"))?
    };

    set_current_project(app, &recent_path)
}

fn reload_main_window<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let window = app
        .get_webview_window(MAIN_WINDOW_LABEL)
        .ok_or_else(|| "Main window not found".to_string())?;
    window
        .eval("window.location.reload()")
        .map_err(|err| err.to_string())
}

fn open_desktop_devtools<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let config = current_config(app)?;
    if !desktop_debug_enabled(&config) {
        return Err("Desktop debug mode is disabled".to_string());
    }

    let window = app
        .get_webview_window(MAIN_WINDOW_LABEL)
        .ok_or_else(|| "Main window not found".to_string())?;
    window.open_devtools();
    Ok(())
}

fn current_config<R: Runtime>(app: &AppHandle<R>) -> Result<AppConfig, String> {
    let state: State<ConfigState> = app.state();
    let config = state.config.lock().map_err(|err| err.to_string())?;
    Ok(config.clone())
}

fn build_recent_projects_submenu<R: Runtime>(
    app: &AppHandle<R>,
    config: &AppConfig,
    labels: &MenuLabels,
) -> tauri::Result<tauri::menu::Submenu<R>> {
    let enabled = !config.recent_projects.is_empty();
    let mut submenu =
        SubmenuBuilder::with_id(app, MENU_OPEN_RECENT_SUBMENU, labels.open_recent).enabled(enabled);

    for (index, entry) in config.recent_projects.iter().enumerate() {
        let item = MenuItemBuilder::with_id(
            format!("{RECENT_PROJECT_ID_PREFIX}{index}"),
            recent_project_label(entry, labels),
        )
        .enabled(AppConfig::validate_project_path(&entry.path).is_ok())
        .build(app)?;
        submenu = submenu.item(&item);
    }

    submenu.build()
}

pub fn build_app_menu<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    let config = current_config(app).map_err(std::io::Error::other)?;
    let labels = labels_for(current_language(&config));

    let open_project = MenuItemBuilder::with_id(MENU_OPEN_PROJECT, labels.open_project)
        .accelerator("CmdOrCtrl+O")
        .build(app)?;
    let settings = MenuItemBuilder::with_id(MENU_SETTINGS, labels.settings)
        .accelerator("CmdOrCtrl+,")
        .build(app)?;
    let command_palette = MenuItemBuilder::with_id(MENU_COMMAND_PALETTE, labels.command_palette)
        .accelerator("CmdOrCtrl+K")
        .build(app)?;
    let toggle_sidebar =
        MenuItemBuilder::with_id(MENU_TOGGLE_SIDEBAR, labels.toggle_sidebar).build(app)?;
    let reload_ui = MenuItemBuilder::with_id(MENU_RELOAD_UI, labels.reload_ui)
        .accelerator("CmdOrCtrl+R")
        .build(app)?;
    let toggle_devtools = MenuItemBuilder::with_id(MENU_TOGGLE_DEVTOOLS, labels.toggle_devtools)
        .accelerator(devtools_accelerator())
        .enabled(desktop_debug_enabled(&config))
        .build(app)?;
    let documentation =
        MenuItemBuilder::with_id(MENU_DOCUMENTATION, labels.documentation).build(app)?;
    let shortcuts = MenuItemBuilder::with_id(MENU_SHORTCUTS, labels.shortcuts).build(app)?;
    let about = MenuItemBuilder::with_id(MENU_ABOUT, labels.about).build(app)?;
    let quit = PredefinedMenuItem::quit(app, labels.quit)?;
    let minimize = PredefinedMenuItem::minimize(app, None)?;
    let maximize = PredefinedMenuItem::maximize(app, None)?;
    let fullscreen = PredefinedMenuItem::fullscreen(app, None)?;
    let close_window = PredefinedMenuItem::close_window(app, None)?;

    let recent_projects = build_recent_projects_submenu(app, &config, &labels)?;

    let file_menu = SubmenuBuilder::new(app, labels.file)
        .item(&open_project)
        .item(&recent_projects)
        .separator()
        .item(&settings)
        .separator()
        .item(&quit)
        .build()?;

    let view_menu = SubmenuBuilder::new(app, labels.view)
        .item(&command_palette)
        .item(&toggle_sidebar)
        .separator()
        .item(&reload_ui)
        .item(&toggle_devtools)
        .build()?;

    let window_menu = SubmenuBuilder::with_id(app, WINDOW_SUBMENU_ID, labels.window)
        .item(&minimize)
        .item(&maximize)
        .item(&fullscreen)
        .separator()
        .item(&close_window)
        .build()?;

    let help_menu = SubmenuBuilder::with_id(app, HELP_SUBMENU_ID, labels.help)
        .item(&documentation)
        .item(&shortcuts)
        .separator()
        .item(&about)
        .build()?;

    Menu::with_items(app, &[&file_menu, &view_menu, &window_menu, &help_menu])
}

pub fn refresh_app_menu<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let menu = build_app_menu(app).map_err(|err| err.to_string())?;
    menu.set_as_app_menu().map_err(|err| err.to_string())?;
    Ok(())
}

pub fn handle_menu_event<R: Runtime>(app: &AppHandle<R>, event: MenuEvent) {
    let menu_id = event.id().as_ref();
    let result = match menu_id {
        MENU_OPEN_PROJECT => open_project_dialog(app),
        MENU_SETTINGS => emit_frontend_action(app, "settings.open"),
        MENU_COMMAND_PALETTE => emit_frontend_action(app, "command_palette.open"),
        MENU_TOGGLE_SIDEBAR => emit_frontend_action(app, "shell.toggle_sidebar"),
        MENU_RELOAD_UI => reload_main_window(app),
        MENU_TOGGLE_DEVTOOLS => open_desktop_devtools(app),
        MENU_DOCUMENTATION => emit_frontend_action(app, "help.documentation"),
        MENU_SHORTCUTS => emit_frontend_action(app, "help.shortcuts"),
        MENU_ABOUT => emit_frontend_action(app, "help.about"),
        id if id.starts_with(RECENT_PROJECT_ID_PREFIX) => {
            let Some(index) = id
                .strip_prefix(RECENT_PROJECT_ID_PREFIX)
                .and_then(|value| value.parse::<usize>().ok())
            else {
                return;
            };
            open_recent_project(app, index)
        }
        _ => Ok(()),
    };

    if let Err(err) = result {
        eprintln!("Failed to handle menu event '{}': {}", menu_id, err);
    }
}
