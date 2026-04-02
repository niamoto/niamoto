use std::net::TcpListener;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{Manager, State};

#[cfg(target_os = "macos")]
use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial};


mod config;
mod commands;

use commands::ConfigState;

const SERVER_STARTUP_TIMEOUT_SECS: u64 = 90;
const SERVER_POLL_INTERVAL_MS: u64 = 500;

/// Shared state to track the FastAPI server process
struct ServerState {
    process: Mutex<Option<Child>>,
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
) -> Result<Child, Box<dyn std::error::Error>> {
    // Determine the executable name based on OS
    let exe_name = if cfg!(target_os = "windows") {
        "niamoto.exe"
    } else {
        "niamoto"
    };

    // Get the current executable path and find sibling binary
    let current_exe = std::env::current_exe()
        .map_err(|e| format!("Failed to get current exe: {}", e))?;
    let exe_dir = current_exe.parent()
        .ok_or("Failed to get exe directory")?;
    let exe_path = exe_dir.join(exe_name);

    println!("Launching FastAPI server from: {:?}", exe_path);

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
    let child = command.spawn()?;

    println!("FastAPI server process started (PID: {})", child.id());
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

    let _ = window.eval(&format!("document.body.innerHTML = `{}`", html.replace("`", "\\`")));
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
            } else {
                println!("No project selected - running in standalone mode");
            }

            let port = find_free_port();
            println!("Selected port: {}", port);

            let app_handle = app.handle().clone();
            let window_clone = window.clone();

            // Spawn sidecar startup in a background thread so the loading screen renders
            thread::spawn(move || {
                // Launch the FastAPI server
                println!("Launching FastAPI server...");

                let server_process = match launch_fastapi_server(
                    &app_handle,
                    port,
                    niamoto_home.as_deref(),
                ) {
                    Ok(process) => process,
                    Err(e) => {
                        let error_msg = format!(
                            "Failed to launch server: {}\n\nMake sure the application was built correctly.",
                            e
                        );
                        eprintln!("{}", error_msg);
                        show_error_screen(&window_clone, &error_msg);
                        return;
                    }
                };

                // Store the process handle for cleanup
                let server_state = app_handle.state::<ServerState>();
                *server_state.process.lock().unwrap() = Some(server_process);

                // Poll for server readiness
                println!("Waiting for server to be ready...");
                show_loading_status(&window_clone, "Waiting for server to be ready...");

                let max_attempts = (SERVER_STARTUP_TIMEOUT_SECS * 1000 / SERVER_POLL_INTERVAL_MS) as u32;
                let mut attempts = 0;

                while !is_server_ready(port) && attempts < max_attempts {
                    thread::sleep(Duration::from_millis(SERVER_POLL_INTERVAL_MS));
                    attempts += 1;

                    if attempts % 10 == 0 {
                        println!("Still waiting... ({}/{})", attempts, max_attempts);
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
                        "Server failed to start after {} seconds.\n\nThe packaged backend may still be starting up or may be missing dependencies.",
                        SERVER_STARTUP_TIMEOUT_SECS
                    );
                    eprintln!("{}", error_msg);
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

                // Navigate to the server URL
                let url = format!("http://127.0.0.1:{}", port);
                println!("Loading URL: {}", url);
                let _ = window_clone.eval(&format!("window.location.replace('{}')", url));

                println!("✓ Niamoto Desktop ready!");
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
