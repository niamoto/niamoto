use std::fs::{create_dir_all, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::{Manager, State};

#[cfg(target_os = "macos")]
use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial};

mod commands;
mod config;

use commands::ConfigState;

const SERVER_STARTUP_TIMEOUT_SECS: u64 = 90;
const SERVER_POLL_INTERVAL_MS: u64 = 500;

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
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    {
        "x86_64-pc-windows-msvc"
    }
}

fn resolve_sidecar_path(
    app_handle: &tauri::AppHandle,
) -> Result<PathBuf, Box<dyn std::error::Error>> {
    let exe_name = sidecar_exe_name();

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

    // Development runs launch directly from the repository virtualenv.
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let project_root = manifest_dir
        .parent()
        .ok_or("Failed to resolve project root from Cargo manifest")?;
    let venv_sidecar = if cfg!(target_os = "windows") {
        project_root.join(".venv").join("Scripts").join(exe_name)
    } else {
        project_root.join(".venv").join("bin").join(exe_name)
    };
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
    let base_dir = dirs::home_dir().unwrap_or_else(std::env::temp_dir);
    let log_dir = base_dir.join(".niamoto").join("logs");
    let _ = create_dir_all(&log_dir);
    log_dir
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

/// Check if the FastAPI server is responding on the given port
fn is_server_ready(port: u16) -> bool {
    match reqwest::blocking::get(format!("http://127.0.0.1:{}/api/health", port)) {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

/// Launch the FastAPI server as a subprocess
fn launch_fastapi_server(
    _app_handle: &tauri::AppHandle,
    port: u16,
    niamoto_home: Option<&str>,
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
    command.env("NIAMOTO_STARTUP_SESSION", startup_session);
    command.env("NIAMOTO_STARTUP_LOG", startup_log_path);
    command.env("PYTHONUNBUFFERED", "1");
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    // Set NIAMOTO_HOME if a project is selected
    if let Some(home) = niamoto_home {
        println!("Setting NIAMOTO_HOME to: {}", home);
        command.env("NIAMOTO_HOME", home);
    } else {
        println!("No project selected - running in standalone mode");
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

/// Show a loading screen with status message
fn show_loading_status(window: &tauri::WebviewWindow, message: &str) {
    let js = format!(
        r#"
        document.body.style.cssText = 'margin:0;padding:0;height:100vh;display:flex;justify-content:center;align-items:center;font-family:system-ui,-apple-system,sans-serif;background:#fff;color:#18181b;user-select:none;';
        document.body.setAttribute('data-tauri-drag-region', '');
        document.body.innerHTML = '<div data-tauri-drag-region style="text-align:center;padding:40px;pointer-events:none;">'
            + '<img src="data:image/png;base64,{icon}" style="width:128px;height:128px;margin:0 auto 32px;display:block;border-radius:16px;" />'
            + '<div style="border:2px solid rgba(0,0,0,0.06);border-radius:50%;border-top:2px solid #a1a1aa;width:24px;height:24px;animation:spin 0.8s linear infinite;margin:0 auto 16px;"></div>'
            + '<p style="font-size:13px;margin:0;color:#a1a1aa;">{msg}</p>'
            + '</div>';
        if (!document.getElementById('_spin')) {{
            var s = document.createElement('style');
            s.id = '_spin';
            s.textContent = '@keyframes spin {{ 0% {{ transform:rotate(0deg) }} 100% {{ transform:rotate(360deg) }} }}';
            document.head.appendChild(s);
        }}
        "#,
        icon = ICON_BASE64.trim(),
        msg = message,
    );

    let _ = window.eval(&js);
}

/// Show an error screen
fn show_error_screen(window: &tauri::WebviewWindow, error: &str) {
    let html = format!(
        r#"
        <style>
            body {{
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: system-ui, -apple-system, sans-serif;
                background: #1a1a1a;
                color: white;
                -webkit-app-region: drag;
                user-select: none;
                cursor: move;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                max-width: 600px;
            }}
            .error-icon {{
                font-size: 72px;
                margin-bottom: 20px;
            }}
            h1 {{
                font-size: 28px;
                margin-bottom: 15px;
                color: #ff6b6b;
            }}
            p {{
                font-size: 16px;
                line-height: 1.6;
                opacity: 0.9;
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 8px;
                font-family: monospace;
            }}
        </style>
        <div class="container">
            <div class="error-icon">⚠️</div>
            <h1>Failed to Start Server</h1>
            <p>{}</p>
        </div>
        "#,
        error.replace("<", "&lt;").replace(">", "&gt;")
    );

    let _ = window.eval(&format!(
        "document.body.innerHTML = `{}`",
        html.replace("`", "\\`")
    ));
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
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
            commands::validate_project,
            commands::get_niamoto_home,
            commands::get_app_settings,
            commands::set_app_settings,
            commands::create_project,
            commands::browse_folder,
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
            } else {
                println!("No project selected - running in standalone mode");
                write_startup_log(
                    &startup_log_path,
                    &startup_session,
                    "rust",
                    "no current project selected",
                );
            }

            let port = find_free_port();
            println!("Selected port: {}", port);
            write_startup_log(
                &startup_log_path,
                &startup_session,
                "rust",
                &format!("selected port {port}"),
            );

            let app_handle = app.handle().clone();
            let window_clone = window.clone();
            let startup_log_path_for_thread = startup_log_path.clone();
            let startup_session_for_thread = startup_session.clone();

            // Spawn sidecar startup in a background thread so the loading screen renders
            thread::spawn(move || {
                let startup_started = Instant::now();
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    "startup thread entered",
                );

                // Launch the FastAPI server
                println!("Launching FastAPI server...");
                let launch_started = Instant::now();

                let server_process = match launch_fastapi_server(
                    &app_handle,
                    port,
                    niamoto_home.as_deref(),
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
                            &format!("sidecar launch failed after {:.3}s: {e}", launch_started.elapsed().as_secs_f64()),
                        );
                        show_error_screen(&window_clone, &error_msg);
                        return;
                    }
                };
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    &format!(
                        "sidecar launch completed in {:.3}s",
                        launch_started.elapsed().as_secs_f64()
                    ),
                );

                // Store the process handle for cleanup
                let server_state = app_handle.state::<ServerState>();
                *server_state.process.lock().unwrap() = Some(server_process);

                // Poll for server readiness
                println!("Waiting for server to be ready...");
                show_loading_status(&window_clone, "Waiting for server to be ready...");

                let max_attempts = (SERVER_STARTUP_TIMEOUT_SECS * 1000 / SERVER_POLL_INTERVAL_MS) as u32;
                let mut attempts = 0;
                let readiness_started = Instant::now();

                while !is_server_ready(port) && attempts < max_attempts {
                    thread::sleep(Duration::from_millis(SERVER_POLL_INTERVAL_MS));
                    attempts += 1;

                    if attempts % 10 == 0 {
                        println!("Still waiting... ({}/{})", attempts, max_attempts);
                        write_startup_log(
                            &startup_log_path_for_thread,
                            &startup_session_for_thread,
                            "rust",
                            &format!(
                                "health still pending after {:.3}s (attempt {attempts}/{max_attempts})",
                                readiness_started.elapsed().as_secs_f64()
                            ),
                        );
                        show_loading_status(
                            &window_clone,
                            &format!(
                                "Still waiting... ({}/{}s)",
                                attempts as u64 * SERVER_POLL_INTERVAL_MS / 1000,
                                SERVER_STARTUP_TIMEOUT_SECS
                            ),
                        );
                    }
                }

                if attempts >= max_attempts {
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
                            "startup timed out after {:.3}s total",
                            startup_started.elapsed().as_secs_f64()
                        ),
                    );
                    let server_state = app_handle.state::<ServerState>();
                    if let Some(mut process) = server_state.process.lock().unwrap().take() {
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
                    show_error_screen(&window_clone, &error_msg);
                    return;
                }

                println!("✓ Server ready on http://127.0.0.1:{}", port);
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    &format!(
                        "health endpoint became ready after {:.3}s (total {:.3}s)",
                        readiness_started.elapsed().as_secs_f64(),
                        startup_started.elapsed().as_secs_f64()
                    ),
                );

                // Navigate to the server URL
                let url = format!("http://127.0.0.1:{}", port);
                println!("Loading URL: {}", url);
                let _ = window_clone.eval(&format!("window.location.replace('{}')", url));

                println!("✓ Niamoto Desktop ready!");
                write_startup_log(
                    &startup_log_path_for_thread,
                    &startup_session_for_thread,
                    "rust",
                    &format!("window navigated to backend after {:.3}s", startup_started.elapsed().as_secs_f64()),
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
