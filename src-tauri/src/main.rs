// Prevents additional console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env::consts::{ARCH, OS};
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
// Splash screen helpers
// ---------------------------------------------------------------------------

/// Embed the splash HTML at compile time and expose it as a `data:` URI
/// so the webview can load it without any file-system access at runtime.
const SPLASH_HTML: &str = include_str!("../frontend/index.html");

/// Minimal base64 encoder (RFC 4648) — avoids adding an external crate.
fn to_base64(data: &[u8]) -> String {
    const T: &[u8; 64] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = Vec::with_capacity((data.len() + 2) / 3 * 4);
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = if chunk.len() > 1 { chunk[1] as u32 } else { 0 };
        let b2 = if chunk.len() > 2 { chunk[2] as u32 } else { 0 };
        let n = (b0 << 16) | (b1 << 8) | b2;
        out.push(T[((n >> 18) & 63) as usize]);
        out.push(T[((n >> 12) & 63) as usize]);
        out.push(if chunk.len() > 1 { T[((n >> 6) & 63) as usize] } else { b'=' });
        out.push(if chunk.len() > 2 { T[(n & 63) as usize] } else { b'=' });
    }
    // SAFETY: base64 alphabet is valid UTF-8
    unsafe { String::from_utf8_unchecked(out) }
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

            // --- Show splash screen immediately via a data: URI ---
            // Using include_str! + base64 avoids any file-system lookup at runtime,
            // which sidesteps the frontendDist path issues in Tauri dev mode.
            if let Some(splash_win) = app.get_webview_window("main") {
                let data_url = format!(
                    "data:text/html;base64,{}",
                    to_base64(SPLASH_HTML.as_bytes())
                );
                if let Ok(url) = data_url.parse::<tauri::Url>() {
                    let _ = splash_win.navigate(url);
                }
            }

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
                let ready = wait_for_health(port, Duration::from_secs(90));

                if let Some(window) = app_handle.get_webview_window("main") {
                    if ready {
                        let url_str = format!("http://127.0.0.1:{port}");
                        if let Ok(url) = url_str.parse::<tauri::Url>() {
                            let _ = window.navigate(url);
                        }
                    } else {
                        // Inject a full error page into the splash webview.
                        // serde_json::to_string encodes the HTML as a JSON string
                        // literal (handles quotes, backslashes, newlines) so it
                        // can be passed safely to document.write().
                        let diag = format!(
                            "Port : {port}\nTimeout : 90 secondes\nSystème : {OS} {ARCH}"
                        );
                        let html = format!(
                            r#"<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Erreur — Tablerreur</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html,body{{height:100%;background:#fff8f8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
    body{{display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:100vh;padding:2rem}}
    .card{{max-width:560px;width:100%}}
    h1{{font-size:1.5rem;font-weight:700;color:#dc2626;margin-bottom:1rem}}
    p{{color:#475569;line-height:1.6;margin-bottom:1rem}}
    pre{{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:1rem;font-size:.85rem;white-space:pre-wrap;user-select:all;color:#334155;margin-bottom:1rem}}
    button{{background:#2563eb;color:#fff;border:none;border-radius:6px;padding:.5rem 1rem;font-size:.875rem;cursor:pointer;font-family:inherit}}
    button:hover{{background:#1d4ed8}}
    .note{{margin-top:1rem;font-size:.8rem;color:#94a3b8}}
  </style>
</head>
<body>
  <div class="card">
    <h1>Erreur de démarrage</h1>
    <p>Le serveur Tablerreur n'a pas pu démarrer dans les délais.</p>
    <pre id="diag">{diag}</pre>
    <button onclick="navigator.clipboard.writeText(document.getElementById('diag').textContent).catch(function(){{}})">
      Copier le diagnostic
    </button>
    <p class="note">Contactez le support avec ces informations.</p>
  </div>
</body>
</html>"#
                        );
                        // Encode HTML as a JSON string for safe injection into JS
                        let json_html = serde_json::to_string(&html)
                            .unwrap_or_else(|_| "\"Erreur de démarrage\"".to_string());
                        let js = format!(
                            "document.open();document.write({json_html});document.close();"
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
