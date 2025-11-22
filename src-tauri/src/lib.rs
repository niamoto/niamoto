use std::net::TcpListener;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{Manager, State};

mod config;
mod commands;

use commands::ConfigState;

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

    // Launch the server
    let child = command.spawn()?;

    println!("FastAPI server process started (PID: {})", child.id());
    Ok(child)
}

/// Show a loading screen with status message
fn show_loading_status(window: &tauri::WebviewWindow, message: &str) {
    let html = format!(
        r#"
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    font-family: system-ui, -apple-system, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    text-align: center;
                    padding: 40px;
                }}
                .spinner {{
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-radius: 50%;
                    border-top: 4px solid white;
                    width: 60px;
                    height: 60px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 30px;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                h1 {{
                    font-size: 28px;
                    margin-bottom: 15px;
                }}
                p {{
                    font-size: 16px;
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="spinner"></div>
                <h1>Niamoto</h1>
                <p>{}</p>
            </div>
        </body>
        </html>
        "#,
        message
    );

    let _ = window.eval(&format!("document.body.innerHTML = `{}`", html.replace("`", "\\`")));
}

/// Show an error screen
fn show_error_screen(window: &tauri::WebviewWindow, error: &str) {
    let html = format!(
        r#"
        <html>
        <head>
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
        </head>
        <body>
            <div class="container">
                <div class="error-icon">⚠️</div>
                <h1>Failed to Start Server</h1>
                <p>{}</p>
            </div>
        </body>
        </html>
        "#,
        error.replace("<", "&lt;").replace(">", "&gt;")
    );

    let _ = window.eval(&format!("document.body.innerHTML = `{}`", html.replace("`", "\\`")));
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
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
        ])
        .setup(|app| {
            println!("Starting Niamoto Desktop Application...");

            let window = app.get_webview_window("main").unwrap();

            let app_handle = app.handle().clone();

            // Show loading screen
            show_loading_status(&window, "Starting server...");

            // Get the current project from config
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

            // 1. Find a free port
            let port = find_free_port();
            println!("Selected port: {}", port);

            // 2. Launch the FastAPI server
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
                    show_error_screen(&window, &error_msg);
                    return Err(e.into());
                }
            };

            // Store the process handle for cleanup later
            let state: State<ServerState> = app.state();
            *state.process.lock().unwrap() = Some(server_process);

            // 3. Wait for the server to be ready (max 30 seconds)
            println!("Waiting for server to be ready...");
            show_loading_status(&window, "Waiting for server to be ready...");

            let max_attempts = 60; // 30 seconds (500ms * 60)
            let mut attempts = 0;

            while !is_server_ready(port) && attempts < max_attempts {
                thread::sleep(Duration::from_millis(500));
                attempts += 1;

                if attempts % 10 == 0 {
                    println!("Still waiting... ({}/{})", attempts, max_attempts);
                    show_loading_status(
                        &window,
                        &format!("Still waiting... ({}/{}s)", attempts / 2, max_attempts / 2),
                    );
                }
            }

            if attempts >= max_attempts {
                let error_msg = "Server failed to start after 30 seconds.\n\nCheck that all dependencies are installed.";
                eprintln!("{}", error_msg);
                show_error_screen(&window, error_msg);
                return Err(error_msg.into());
            }

            println!("✓ Server ready on http://127.0.0.1:{}", port);

            // 4. Load the URL in the main window
            let url = format!("http://127.0.0.1:{}", port);
            println!("Loading URL: {}", url);

            // Navigate to the server URL
            window
                .eval(&format!("window.location.replace('{}')", url))
                .expect("Failed to load URL in webview");

            println!("✓ Niamoto Desktop ready!");

            Ok(())
        })
        // Clean shutdown of FastAPI server
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                println!("Window close requested, killing server...");
                let state: State<ServerState> = window.state();
                if let Some(mut process) = state.process.lock().unwrap().take() {
                    println!("Killing FastAPI server (PID: {})", process.id());
                    let _ = process.kill();
                    let _ = process.wait();
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
