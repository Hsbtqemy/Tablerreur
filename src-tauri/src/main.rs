// Prevents additional console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpListener;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, menu::{MenuBuilder, SubmenuBuilder, MenuItemBuilder}};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

// ---------------------------------------------------------------------------
// Networking helpers
// ---------------------------------------------------------------------------

/// Return the first free TCP port in [start, end), or None if all are taken.
fn find_free_port(start: u16, end: u16) -> Option<u16> {
    for port in start..end {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return Some(port);
        }
    }
    None
}

/// Poll TCP connectivity on 127.0.0.1:{port} every 200 ms up to *timeout*.
/// Returns true as soon as the port accepts connections.
fn wait_for_health(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    loop {
        let addr = format!("127.0.0.1:{port}");
        if let Ok(addr) = addr.parse() {
            if std::net::TcpStream::connect_timeout(&addr, Duration::from_millis(500)).is_ok() {
                return true;
            }
        }
        if Instant::now() >= deadline {
            return false;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
}

// ---------------------------------------------------------------------------
// Managed state: keeps the sidecar child alive for the app lifetime
// ---------------------------------------------------------------------------

struct SidecarState(Mutex<Option<CommandChild>>);

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // --- Build native menu ---
            let quit_item = MenuItemBuilder::new("Quitter")
                .id("quit")
                .accelerator("CmdOrCtrl+Q")
                .build(app)?;
            let file_menu = SubmenuBuilder::new(app, "Fichier")
                .item(&quit_item)
                .build()?;

            let updates_item = MenuItemBuilder::new("Vérifier les mises à jour")
                .id("check-updates")
                .build(app)?;
            let help_menu = SubmenuBuilder::new(app, "Aide")
                .item(&updates_item)
                .build()?;

            let menu = MenuBuilder::new(app)
                .item(&file_menu)
                .item(&help_menu)
                .build()?;
            app.set_menu(menu)?;

            // --- Find a free port ---
            let port = find_free_port(8400, 8500)
                .expect("Aucun port libre trouvé entre 8400 et 8500");

            // --- Launch the Python sidecar ---
            let sidecar_cmd = app
                .shell()
                .sidecar("tablerreur-backend")?
                .args(["--port", &port.to_string()]);
            let (_rx, child) = sidecar_cmd.spawn()?;

            // Keep sidecar alive in managed state
            app.manage(SidecarState(Mutex::new(Some(child))));

            // --- Background thread: poll health then navigate ---
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                let ready = wait_for_health(port, Duration::from_secs(15));

                if let Some(window) = app_handle.get_webview_window("main") {
                    if ready {
                        let url_str = format!("http://127.0.0.1:{port}");
                        if let Ok(url) = url_str.parse::<tauri::Url>() {
                            let _ = window.navigate(url);
                        }
                    } else {
                        // Show error in the webview using JavaScript
                        let msg = format!(
                            "Le serveur Tablerreur n'a pas pu démarrer.\\n\\n\
                             Port : {port}\\n\
                             Diagnostic : le backend n'a pas répondu dans les 15 secondes.\\n\\n\
                             Copiez ce message et contactez le support."
                        );
                        let escaped = msg.replace('\\', "\\\\").replace('\'', "\\'");
                        let js = format!(
                            "document.body.innerHTML = \
                             '<div style=\"font-family:sans-serif;padding:2rem;max-width:600px\">\
                             <h2 style=\"color:#c62828\">Erreur de démarrage</h2>\
                             <pre style=\"white-space:pre-wrap;background:#f5f5f5;padding:1rem;\
                             border-radius:4px;user-select:all\">{escaped}</pre></div>'"
                        );
                        let _ = window.eval(&js);
                    }
                }
            });

            Ok(())
        })
        .on_menu_event(|app, event| {
            match event.id().as_ref() {
                "quit" => app.exit(0),
                "check-updates" => {
                    // Open releases page in the default browser
                    let _ = app.opener().open_url(
                        "https://github.com/VOTRE_ORGANISATION/tablerreur/releases",
                        None::<&str>,
                    );
                }
                _ => {}
            }
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill the sidecar when the window is closed
                if let Some(state) = window.app_handle().try_state::<SidecarState>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Erreur lors du lancement de Tablerreur");
}
