use rand::RngCore;
use std::fs::OpenOptions;
use std::io::{BufRead, BufReader, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::{Manager, State, Url};

#[cfg(target_os = "macos")]
use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial};

mod commands;
mod config;

use commands::ConfigState;
use config::{AppConfig, DESKTOP_CONFIG_ENV, DESKTOP_LOG_DIR_ENV};

const SERVER_STARTUP_TIMEOUT_SECS: u64 = 90;
const SERVER_POLL_INTERVAL_MS: u64 = 500;
const SERVER_STARTUP_RETRY_LIMIT: u32 = 3;
const DEV_API_PORT: u16 = 8080;
const DESKTOP_PROBE_HEADER: &str = "x-niamoto-desktop-probe";
const DESKTOP_TOKEN_HEADER: &str = "x-niamoto-desktop-token";
const APP_LOADER_CSS: &str =
    include_str!("../../src/niamoto/gui/ui/src/styles/app-loader.css");

/// Shared state to track the FastAPI server process
struct ServerState {
    process: Mutex<Option<Child>>,
}

fn sidecar_exe_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "niamoto.exe"
    } else {
        "niamoto"
    }
}

fn sidecar_target_triple() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    {
        "aarch64-apple-darwin"
    }
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    {
        "x86_64-apple-darwin"
    }
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    {
        "x86_64-unknown-linux-gnu"
    }
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    {
        "aarch64-unknown-linux-gnu"
    }
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    {
        "x86_64-pc-windows-msvc"
    }
    #[cfg(all(target_os = "windows", target_arch = "aarch64"))]
    {
        "aarch64-pc-windows-msvc"
    }
}

fn resolve_sidecar_path(
    app_handle: &tauri::AppHandle,
) -> Result<PathBuf, Box<dyn std::error::Error>> {
    let exe_name = sidecar_exe_name();
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let project_root = manifest_dir
        .parent()
        .ok_or("Failed to resolve project root from Cargo manifest")?;

    // In development, prefer the repository virtualenv so the desktop app
    // always runs against the current Python code and frontend build.
    let venv_sidecar = if cfg!(target_os = "windows") {
        project_root.join(".venv").join("Scripts").join(exe_name)
    } else {
        project_root.join(".venv").join("bin").join(exe_name)
    };

    if cfg!(debug_assertions) && venv_sidecar.exists() {
        return Ok(venv_sidecar);
    }

    // Release bundles ship the PyInstaller onedir sidecar inside Tauri resources.
    if let Ok(resource_dir) = app_handle.path().resource_dir() {
        let bundled_sidecar = resource_dir
            .join("sidecar")
            .join(sidecar_target_triple())
            .join("niamoto")
            .join(exe_name);
        if bundled_sidecar.exists() {
            return Ok(bundled_sidecar);
        }
    }

    // Fallback for environments where the bundled sidecar is not present.
    if venv_sidecar.exists() {
        return Ok(venv_sidecar);
    }

    // Last resort: sibling executable path, for older bundles still using externalBin.
    let current_exe =
        std::env::current_exe().map_err(|e| format!("Failed to get current exe: {}", e))?;
    let exe_dir = current_exe.parent().ok_or("Failed to get exe directory")?;
    Ok(exe_dir.join(exe_name))
}

fn startup_log_dir() -> PathBuf {
    AppConfig::desktop_log_dir()
}

fn initialize_desktop_environment() {
    if std::env::var_os(DESKTOP_CONFIG_ENV).is_none() {
        if let Ok(config_path) = AppConfig::config_path() {
            std::env::set_var(DESKTOP_CONFIG_ENV, &config_path);
        }
    }

    if std::env::var_os(DESKTOP_LOG_DIR_ENV).is_none() {
        let log_dir = AppConfig::desktop_log_dir();
        std::env::set_var(DESKTOP_LOG_DIR_ENV, &log_dir);
    }
}

fn new_startup_session() -> String {
    let now_ms = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    format!("desktop-startup-{}-{}", std::process::id(), now_ms)
}

fn write_startup_log(log_path: &Path, session: &str, source: &str, message: &str) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64();

    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "[{timestamp:.3}] [{session}] [{source}] {message}");
    }
}

fn spawn_startup_stream_logger<R>(
    reader: R,
    log_path: PathBuf,
    session: String,
    source: &'static str,
) where
    R: std::io::Read + Send + 'static,
{
    thread::spawn(move || {
        let buffered = BufReader::new(reader);
        for line in buffered.lines() {
            match line {
                Ok(line) => write_startup_log(&log_path, &session, source, &line),
                Err(err) => {
                    write_startup_log(
                        &log_path,
                        &session,
                        source,
                        &format!("failed to read child stream: {err}"),
                    );
                    break;
                }
            }
        }
    });
}

/// Find an available TCP port by binding to port 0 and letting the OS choose
fn find_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("Failed to bind to any port")
        .local_addr()
        .expect("Failed to get local address")
        .port()
}

fn desktop_hot_reload_enabled() -> bool {
    cfg!(debug_assertions)
        && std::env::var("NIAMOTO_TAURI_DEV_UI")
            .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "YES"))
            .unwrap_or(false)
}

fn desktop_devtools_auto_open_enabled() -> bool {
    cfg!(debug_assertions)
        && std::env::var("NIAMOTO_OPEN_DEVTOOLS")
            .map(|value| {
                matches!(
                    value.trim().to_ascii_lowercase().as_str(),
                    "1" | "true" | "yes" | "on"
                )
            })
            .unwrap_or(false)
}

fn desktop_api_port() -> u16 {
    if desktop_hot_reload_enabled() {
        std::env::var("NIAMOTO_DESKTOP_API_PORT")
            .ok()
            .and_then(|value| value.parse::<u16>().ok())
            .unwrap_or(DEV_API_PORT)
    } else {
        find_free_port()
    }
}

fn generate_startup_token() -> String {
    let mut bytes = [0_u8; 32];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn health_probe_is_authenticated(
    status: reqwest::StatusCode,
    returned_token: Option<&str>,
    expected_token: &str,
) -> bool {
    status.is_success() && returned_token == Some(expected_token)
}

/// Check if the FastAPI server is responding on the given port
fn is_server_ready(port: u16, expected_token: &str) -> bool {
    let client = match reqwest::blocking::Client::builder()
        .timeout(Duration::from_millis(750))
        .build()
    {
        Ok(client) => client,
        Err(_) => return false,
    };

    match client
        .get(format!("http://127.0.0.1:{port}/api/health"))
        .header(DESKTOP_PROBE_HEADER, "1")
        .send()
    {
        Ok(response) => {
            let status = response.status();
            let returned_token = response
                .headers()
                .get(DESKTOP_TOKEN_HEADER)
                .and_then(|value| value.to_str().ok());
            health_probe_is_authenticated(status, returned_token, expected_token)
        }
        Err(_) => false,
    }
}

fn terminate_child_process(process: &mut Child) {
    let pid = process.id();

    #[cfg(target_os = "windows")]
    {
        let _ = std::process::Command::new("taskkill")
            .args(&["/F", "/T", "/PID", &pid.to_string()])
            .output();
    }

    #[cfg(unix)]
    {
        unsafe {
            libc::kill(-(pid as i32), libc::SIGTERM);
        }
        thread::sleep(Duration::from_millis(500));
    }

    let _ = process.kill();
    let _ = process.wait();
}

/// Launch the FastAPI server as a subprocess
fn launch_fastapi_server(
    _app_handle: &tauri::AppHandle,
    port: u16,
    niamoto_home: Option<&str>,
    desktop_auth_token: &str,
    startup_session: &str,
    startup_log_path: &Path,
) -> Result<Child, Box<dyn std::error::Error>> {
    let exe_path = resolve_sidecar_path(_app_handle)?;

    write_startup_log(
        startup_log_path,
        startup_session,
        "rust",
        &format!("launching sidecar from {:?}", exe_path),
    );

    // Build command with environment variables
    let mut command = Command::new(&exe_path);
    command.args(&[
        "gui",
        "--port",
        &port.to_string(),
        "--no-browser",
        "--host",
        "127.0.0.1",
    ]);

    // Set NIAMOTO_RUNTIME_MODE to indicate we're in desktop mode
    command.env("NIAMOTO_RUNTIME_MODE", "desktop");
    command.env("NIAMOTO_DESKTOP_AUTH_TOKEN", desktop_auth_token);
    command.env("NIAMOTO_STARTUP_SESSION", startup_session);
    command.env("NIAMOTO_STARTUP_LOG", startup_log_path);
    if niamoto_home.is_none() {
        command.env("NIAMOTO_LOGS", startup_log_dir());
    }
    command.env("PYTHONUNBUFFERED", "1");
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    // Set NIAMOTO_HOME if a project is selected
    if let Some(home) = niamoto_home {
        println!("Setting NIAMOTO_HOME to: {}", home);
        command.env("NIAMOTO_HOME", home);
    }

    // On Unix, start the sidecar in its own process group
    // so we can kill the entire group on shutdown
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }

    // Launch the server
    let mut child = command.spawn()?;
    let pid = child.id();

    write_startup_log(
        startup_log_path,
        startup_session,
        "rust",
        &format!("sidecar spawned with pid={pid}"),
    );

    if let Some(stdout) = child.stdout.take() {
        spawn_startup_stream_logger(
            stdout,
            startup_log_path.to_path_buf(),
            startup_session.to_string(),
            "sidecar:stdout",
        );
    }

    if let Some(stderr) = child.stderr.take() {
        spawn_startup_stream_logger(
            stderr,
            startup_log_path.to_path_buf(),
            startup_session.to_string(),
            "sidecar:stderr",
        );
    }

    Ok(child)
}

/// Icon PNG encoded as base64 (src-tauri/icons/128x128.png)
const ICON_BASE64: &str = include_str!("../icons/icon_base64.txt");

fn escape_html(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}

fn encode_data_url_component(value: &str) -> String {
    let mut encoded = String::with_capacity(value.len());
    for byte in value.bytes() {
        match byte {
            b'A'..=b'Z'
            | b'a'..=b'z'
            | b'0'..=b'9'
            | b'-'
            | b'_'
            | b'.'
            | b'~' => encoded.push(byte as char),
            _ => encoded.push_str(&format!("%{:02X}", byte)),
        }
    }
    encoded
}

fn navigate_inline_html(window: &tauri::WebviewWindow, html: &str) {
    let data_url = format!(
        "data:text/html;charset=utf-8,{}",
        encode_data_url_component(html)
    );
    if let Ok(url) = Url::parse(&data_url) {
        let _ = window.navigate(url);
    }
}

fn startup_ready_url(
    hot_reload_enabled: bool,
    dev_url: Option<&Url>,
    ready_port: u16,
) -> Result<Url, String> {
    if hot_reload_enabled {
        return dev_url
            .cloned()
            .ok_or_else(|| "Missing devUrl for desktop hot reload mode".to_string());
    }

    Url::parse(&format!("http://127.0.0.1:{ready_port}"))
        .map_err(|err| format!("Invalid backend startup URL: {err}"))
}

/// Show a loading screen with status message
fn show_loading_status(window: &tauri::WebviewWindow, _message: &str) {
    let html = format!(
        r#"<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Niamoto</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #ffffff;
        color: #18181b;
        user-select: none;
      }}
      .shell {{
        padding: 40px;
        --niamoto-loader-color: #2d7a3a;
      }}
      {loader_css}
      @media (prefers-color-scheme: dark) {{
        body {{
          background: #18181b;
          color: #fafafa;
        }}
        .shell {{
          --niamoto-loader-color: #95c98a;
        }}
      }}
    </style>
  </head>
  <body data-tauri-drag-region>
    <main class="shell niamoto-app-loader-shell" data-tauri-drag-region>
      <img class="niamoto-app-loader-logo" alt="" src="data:image/png;base64,{icon}" />
      <div class="niamoto-app-loader niamoto-app-loader--pulse-ring" aria-hidden="true"></div>
    </main>
  </body>
</html>"#,
        icon = ICON_BASE64.trim(),
        loader_css = APP_LOADER_CSS,
    );

    navigate_inline_html(window, &html);
}

/// Show an error screen
fn show_error_screen(window: &tauri::WebviewWindow, error: &str) {
    let html = format!(
        r#"<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Niamoto</title>
    <style>
      :root {{
        color-scheme: dark;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 32px;
        background: #18181b;
        color: #fafafa;
        user-select: none;
      }}
      .shell {{
        max-width: 720px;
        text-align: center;
      }}
      .icon {{
        font-size: 72px;
        margin-bottom: 20px;
      }}
      h1 {{
        margin: 0 0 15px;
        font-size: 28px;
        color: #f87171;
      }}
      p {{
        margin: 0;
        padding: 20px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.92);
        font: 16px/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        white-space: pre-wrap;
        text-align: left;
      }}
    </style>
  </head>
  <body data-tauri-drag-region>
    <main class="shell" data-tauri-drag-region>
      <div class="icon" aria-hidden="true">⚠️</div>
      <h1>Failed to Start Server</h1>
      <p>{message}</p>
    </main>
  </body>
</html>"#,
        message = escape_html(error),
    );

    navigate_inline_html(window, &html);
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    initialize_desktop_environment();

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .manage(ServerState {
            process: Mutex::new(None),
        })
        .manage(ConfigState::new())
        .invoke_handler(tauri::generate_handler![
            commands::get_current_project,
            commands::get_recent_projects,
            commands::set_current_project,
            commands::remove_recent_project,
            commands::browse_project_folder,
            commands::validate_recent_projects,
            commands::validate_project,
            commands::get_niamoto_home,
            commands::get_app_settings,
            commands::set_app_settings,
            commands::open_desktop_devtools,
            commands::create_project,
            commands::browse_folder,
            commands::open_external_url,
        ])
        .setup(|app| {
            println!("Starting Niamoto Desktop Application...");

            let window = app.get_webview_window("main").unwrap();
            let startup_session = new_startup_session();
            let startup_log_path = startup_log_dir().join(format!("{startup_session}.log"));
            write_startup_log(
                &startup_log_path,
                &startup_session,
                "rust",
                "desktop setup started",
            );

            // Apply vibrancy effect with rounded corners on macOS
            // The radius parameter (10.0) handles corner rounding directly
            #[cfg(target_os = "macos")]
            {
                apply_vibrancy(&window, NSVisualEffectMaterial::HudWindow, None, Some(10.0))
                    .expect("Failed to apply vibrancy effect");
                println!("✓ Applied macOS vibrancy with rounded corners");
            }

            // Register updater plugin (desktop only)
            #[cfg(desktop)]
            app.handle().plugin(tauri_plugin_updater::Builder::new().build())?;

            // Show loading screen immediately — setup must return fast
            // so the Tauri event loop can render the window
            show_loading_status(&window, "Starting server...");

            #[cfg(debug_assertions)]
            if desktop_devtools_auto_open_enabled() {
                window.open_devtools();
            }

            // Gather config before spawning the background thread
            let config_state: State<ConfigState> = app.state();
            let niamoto_home = {
                let config = config_state.config.lock().unwrap();
                config.get_current_project_str()
            };

            if let Some(ref home) = niamoto_home {
                println!("Current project: {}", home);
                write_startup_log(
                    &startup_log_path,
                    &startup_session,
                    "rust",
                    &format!("current project set to {home}"),
                );
            }

            let hot_reload_enabled = desktop_hot_reload_enabled();
            let port = desktop_api_port();
            let desktop_auth_token = generate_startup_token();
            println!("Selected port: {}", port);
            write_startup_log(
                &startup_log_path,
                &startup_session,
                "rust",
                &format!("selected port {port}"),
            );
            write_startup_log(
                &startup_log_path,
                &startup_session,
                "rust",
                "generated desktop startup probe token",
            );
            if hot_reload_enabled {
                println!("Desktop hot reload mode enabled via Vite dev server");
                write_startup_log(
                    &startup_log_path,
                    &startup_session,
                    "rust",
                    "desktop hot reload mode enabled",
                );
            }

            let app_handle = app.handle().clone();
            let window_clone = window.clone();
            let startup_log_path_for_thread = startup_log_path.clone();
            let startup_session_for_thread = startup_session.clone();
            let desktop_auth_token_for_thread = desktop_auth_token.clone();

            // Spawn sidecar startup in a background thread so the loading screen renders
            thread::spawn(move || {
                let startup_started = Instant::now();
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    "startup thread entered",
                );

                // Launch the FastAPI server and retry on port races in production mode.
                let mut current_port = port;
                let mut launch_attempt = 1;

                let ready_port = loop {
                    println!(
                        "Launching FastAPI server (attempt {}/{}) on port {}...",
                        launch_attempt,
                        SERVER_STARTUP_RETRY_LIMIT,
                        current_port
                    );
                    let launch_started = Instant::now();

                    let server_process = match launch_fastapi_server(
                        &app_handle,
                        current_port,
                        niamoto_home.as_deref(),
                        &desktop_auth_token_for_thread,
                        &startup_session_for_thread,
                        &startup_log_path_for_thread,
                    ) {
                        Ok(process) => process,
                        Err(e) => {
                            let error_msg = format!(
                                "Failed to launch server: {}\n\nMake sure the application was built correctly.\n\nStartup log: {}",
                                e,
                                startup_log_path_for_thread.display()
                            );
                            eprintln!("{}", error_msg);
                            write_startup_log(
                                &startup_log_path_for_thread,
                                &startup_session_for_thread,
                                "rust",
                                &format!(
                                    "sidecar launch failed on port {current_port} after {:.3}s: {e}",
                                    launch_started.elapsed().as_secs_f64()
                                ),
                            );
                            show_error_screen(&window_clone, &error_msg);
                            return;
                        }
                    };
                    let mut server_process = Some(server_process);
                    write_startup_log(
                        &startup_log_path_for_thread,
                        &startup_session_for_thread,
                        "rust",
                        &format!(
                            "sidecar launch attempt {launch_attempt} completed on port {current_port} in {:.3}s",
                            launch_started.elapsed().as_secs_f64()
                        ),
                    );

                    println!("Waiting for server to be ready...");
                    show_loading_status(&window_clone, "Waiting for server to be ready...");

                    let max_attempts =
                        (SERVER_STARTUP_TIMEOUT_SECS * 1000 / SERVER_POLL_INTERVAL_MS) as u32;
                    let mut attempts = 0;
                    let readiness_started = Instant::now();
                    let mut exited_early = None;

                    while attempts < max_attempts {
                        if is_server_ready(current_port, &desktop_auth_token_for_thread) {
                            let server_state = app_handle.state::<ServerState>();
                            *server_state.process.lock().unwrap() = server_process.take();
                            break;
                        }

                        match server_process
                            .as_mut()
                            .expect("server process missing before readiness")
                            .try_wait()
                        {
                            Ok(Some(status)) => {
                                exited_early = Some(status);
                                break;
                            }
                            Ok(None) => {}
                            Err(err) => {
                                write_startup_log(
                                    &startup_log_path_for_thread,
                                    &startup_session_for_thread,
                                    "rust",
                                    &format!("failed to query sidecar status on port {current_port}: {err}"),
                                );
                            }
                        }

                        thread::sleep(Duration::from_millis(SERVER_POLL_INTERVAL_MS));
                        attempts += 1;

                        if attempts % 10 == 0 {
                            println!("Still waiting... ({}/{})", attempts, max_attempts);
                            write_startup_log(
                                &startup_log_path_for_thread,
                                &startup_session_for_thread,
                                "rust",
                                &format!(
                                    "health still pending on port {current_port} after {:.3}s (attempt {attempts}/{max_attempts})",
                                    readiness_started.elapsed().as_secs_f64()
                                ),
                            );
                            show_loading_status(&window_clone, "Still waiting...");
                        }
                    }

                    if is_server_ready(current_port, &desktop_auth_token_for_thread) {
                        write_startup_log(
                            &startup_log_path_for_thread,
                            &startup_session_for_thread,
                            "rust",
                            &format!(
                                "health endpoint became ready on port {current_port} after {:.3}s (total {:.3}s)",
                                readiness_started.elapsed().as_secs_f64(),
                                startup_started.elapsed().as_secs_f64()
                            ),
                        );
                        break current_port;
                    }

                    if let Some(status) = exited_early {
                        let exit_note = status
                            .code()
                            .map(|code| format!("exit code {code}"))
                            .unwrap_or_else(|| "terminated by signal".to_string());
                        write_startup_log(
                            &startup_log_path_for_thread,
                            &startup_session_for_thread,
                            "rust",
                            &format!(
                                "sidecar exited before health became ready on port {current_port} ({exit_note})"
                            ),
                        );

                        if hot_reload_enabled {
                            let error_msg = format!(
                                "Server exited before becoming ready on port {}.\n\nDesktop dev mode requires the API port to stay fixed for the Vite proxy. Ensure port {} is free or change NIAMOTO_DESKTOP_API_PORT, then relaunch.\n\nStartup log: {}",
                                current_port,
                                current_port,
                                startup_log_path_for_thread.display()
                            );
                            show_error_screen(&window_clone, &error_msg);
                            return;
                        }

                        if launch_attempt < SERVER_STARTUP_RETRY_LIMIT {
                            launch_attempt += 1;
                            current_port = find_free_port();
                            write_startup_log(
                                &startup_log_path_for_thread,
                                &startup_session_for_thread,
                                "rust",
                                &format!(
                                    "retrying sidecar startup on new port {current_port} (attempt {launch_attempt}/{SERVER_STARTUP_RETRY_LIMIT})"
                                ),
                            );
                            show_loading_status(&window_clone, "Retrying server startup...");
                            continue;
                        }

                        let error_msg = format!(
                            "Server exited before becoming ready after {} attempts.\n\nStartup log: {}",
                            SERVER_STARTUP_RETRY_LIMIT,
                            startup_log_path_for_thread.display()
                        );
                        show_error_screen(&window_clone, &error_msg);
                        return;
                    }

                    let error_msg = format!(
                        "Server failed to start after {} seconds.\n\nThe packaged backend may still be starting up or may be missing dependencies.\n\nStartup log: {}",
                        SERVER_STARTUP_TIMEOUT_SECS,
                        startup_log_path_for_thread.display()
                    );
                    eprintln!("{}", error_msg);
                    write_startup_log(
                        &startup_log_path_for_thread,
                        &startup_session_for_thread,
                        "rust",
                        &format!(
                            "startup timed out on port {current_port} after {:.3}s total",
                            startup_started.elapsed().as_secs_f64()
                        ),
                    );
                    if let Some(mut process) = server_process.take() {
                        terminate_child_process(&mut process);
                    }
                    show_error_screen(&window_clone, &error_msg);
                    return;
                };

                println!("✓ Server ready on http://127.0.0.1:{}", ready_port);
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    &format!("server ready on http://127.0.0.1:{ready_port}"),
                );

                let startup_url = startup_ready_url(
                    hot_reload_enabled,
                    app_handle.config().build.dev_url.as_ref(),
                    ready_port,
                );
                match startup_url {
                    Ok(url) => {
                        println!("Loading URL: {}", url);
                        let _ = window_clone.navigate(url);
                        write_startup_log(
                            &startup_log_path_for_thread,
                            &startup_session_for_thread,
                            "rust",
                            if hot_reload_enabled {
                                "navigated back to Vite dev server after backend readiness"
                            } else {
                                "window navigated to backend after startup"
                            },
                        );
                    }
                    Err(error_msg) => {
                        show_error_screen(&window_clone, &error_msg);
                        write_startup_log(
                            &startup_log_path_for_thread,
                            &startup_session_for_thread,
                            "rust",
                            &format!("failed to resolve startup URL: {error_msg}"),
                        );
                        return;
                    }
                }

                println!("✓ Niamoto Desktop ready!");
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    &format!("desktop startup completed after {:.3}s", startup_started.elapsed().as_secs_f64()),
                );
            });

            Ok(())
        })
        // Clean shutdown of FastAPI server — kill the entire process tree
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                println!("Window close requested, killing server...");
                let state: State<ServerState> = window.state();
                if let Some(mut process) = state.process.lock().unwrap().take() {
                    let pid = process.id();
                    println!("Killing FastAPI server (PID: {})", pid);

                    #[cfg(target_os = "windows")]
                    {
                        // Kill the entire process tree on Windows
                        let _ = std::process::Command::new("taskkill")
                            .args(&["/F", "/T", "/PID", &pid.to_string()])
                            .output();
                    }

                    #[cfg(unix)]
                    {
                        // Kill the process group on Unix
                        unsafe {
                            libc::kill(-(pid as i32), libc::SIGTERM);
                        }
                        // Brief wait for graceful shutdown
                        thread::sleep(Duration::from_millis(500));
                    }

                    // Fallback: force kill the direct child
                    let _ = process.kill();
                    let _ = process.wait();
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::{generate_startup_token, health_probe_is_authenticated};
    use super::startup_ready_url;
    use tauri::Url;

    #[test]
    fn generate_startup_token_returns_64_hex_chars() {
        let token = generate_startup_token();
        assert_eq!(token.len(), 64);
        assert!(token.chars().all(|ch| ch.is_ascii_hexdigit()));
    }

    #[test]
    fn health_probe_requires_matching_token() {
        assert!(health_probe_is_authenticated(
            reqwest::StatusCode::OK,
            Some("secret"),
            "secret"
        ));
        assert!(!health_probe_is_authenticated(
            reqwest::StatusCode::OK,
            Some("wrong"),
            "secret"
        ));
        assert!(!health_probe_is_authenticated(
            reqwest::StatusCode::OK,
            None,
            "secret"
        ));
        assert!(!health_probe_is_authenticated(
            reqwest::StatusCode::INTERNAL_SERVER_ERROR,
            Some("secret"),
            "secret"
        ));
    }

    #[test]
    fn startup_ready_url_uses_dev_url_in_hot_reload_mode() {
        let dev_url = Url::parse("http://127.0.0.1:5173").unwrap();
        let resolved = startup_ready_url(true, Some(&dev_url), 8080).unwrap();
        assert_eq!(resolved, dev_url);
    }

    #[test]
    fn startup_ready_url_uses_backend_url_in_release_mode() {
        let resolved = startup_ready_url(false, None, 8080).unwrap();
        assert_eq!(resolved.as_str(), "http://127.0.0.1:8080/");
    }

    #[test]
    fn startup_ready_url_requires_dev_url_in_hot_reload_mode() {
        let error = startup_ready_url(true, None, 8080).unwrap_err();
        assert!(error.contains("Missing devUrl"));
    }
}
