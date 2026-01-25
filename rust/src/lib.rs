//! Native acceleration for matuwrap CLI tool.
//!
//! Provides fast implementations of:
//! - Hyprland IPC via Unix socket (no subprocess overhead)
//! - Matugen color caching with mtime validation
//! - PipeWire sink enumeration via pw-dump
//! - System information queries

use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::Command;
use std::time::SystemTime;

// ============================================================================
// Command execution
// ============================================================================

/// Run a command and return stdout as string.
#[pyfunction]
fn run_command(program: &str, args: Vec<String>) -> PyResult<String> {
    let output = Command::new(program)
        .args(&args)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            stderr.to_string(),
        ));
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

// ============================================================================
// Hyprland IPC
// ============================================================================

/// Query Hyprland IPC directly via Unix socket.
#[pyfunction]
fn hyprctl(command: &str) -> PyResult<String> {
    let his = std::env::var("HYPRLAND_INSTANCE_SIGNATURE").map_err(|_| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("HYPRLAND_INSTANCE_SIGNATURE not set")
    })?;

    // Try XDG_RUNTIME_DIR first (Hyprland 0.40+), fallback to /tmp
    let socket_path = if let Ok(xdg) = std::env::var("XDG_RUNTIME_DIR") {
        let xdg_path = format!("{}/hypr/{}/.socket.sock", xdg, his);
        if std::path::Path::new(&xdg_path).exists() {
            xdg_path
        } else {
            format!("/tmp/hypr/{}/.socket.sock", his)
        }
    } else {
        format!("/tmp/hypr/{}/.socket.sock", his)
    };

    let mut stream = UnixStream::connect(&socket_path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyConnectionError, _>(format!(
            "Failed to connect to Hyprland socket: {}",
            e
        ))
    })?;

    stream
        .write_all(command.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut response = String::new();
    stream
        .read_to_string(&mut response)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    Ok(response)
}

/// Query Hyprland IPC with JSON output.
#[pyfunction]
fn hyprctl_json(command: &str) -> PyResult<String> {
    hyprctl(&format!("j/{}", command))
}

// ============================================================================
// Matugen color caching
// ============================================================================

#[derive(Serialize, Deserialize)]
struct ColorCache {
    wallpaper_path: String,
    wallpaper_mtime: u64,
    colors: HashMap<String, String>,
}

fn get_cache_path() -> Option<PathBuf> {
    dirs::cache_dir().map(|p| p.join("matuwrap").join("colors.json"))
}

fn get_mtime(path: &str) -> Option<u64> {
    fs::metadata(path)
        .ok()?
        .modified()
        .ok()?
        .duration_since(SystemTime::UNIX_EPOCH)
        .ok()
        .map(|d| d.as_secs())
}

fn load_cache(wallpaper_path: &str) -> Option<HashMap<String, String>> {
    let cache_path = get_cache_path()?;
    let data = fs::read_to_string(&cache_path).ok()?;
    let cache: ColorCache = serde_json::from_str(&data).ok()?;

    // Validate cache
    if cache.wallpaper_path != wallpaper_path {
        return None;
    }

    let current_mtime = get_mtime(wallpaper_path)?;
    if cache.wallpaper_mtime != current_mtime {
        return None;
    }

    Some(cache.colors)
}

fn save_cache(wallpaper_path: &str, colors: &HashMap<String, String>) -> Option<()> {
    let cache_path = get_cache_path()?;
    fs::create_dir_all(cache_path.parent()?).ok()?;

    let cache = ColorCache {
        wallpaper_path: wallpaper_path.to_string(),
        wallpaper_mtime: get_mtime(wallpaper_path)?,
        colors: colors.clone(),
    };

    let json = serde_json::to_string(&cache).ok()?;
    fs::write(&cache_path, json).ok()?;
    Some(())
}

fn run_matugen(wallpaper_path: &str) -> Option<HashMap<String, String>> {
    let output = Command::new("matugen")
        .args([
            "image",
            wallpaper_path,
            "--dry-run",
            "--json",
            "hex",
            "--type",
            "scheme-tonal-spot",
            "--mode",
            "dark",
        ])
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let stdout = String::from_utf8_lossy(&output.stdout);

    // Parse JSON (matugen outputs on stdout)
    let json: serde_json::Value = serde_json::from_str(&stdout).ok()?;
    let colors_obj = json.get("colors")?;

    let mut colors = HashMap::new();
    if let Some(obj) = colors_obj.as_object() {
        for (key, val) in obj {
            // Extract dark mode value
            let color = if let Some(dark) = val.get("dark").and_then(|v| v.as_str()) {
                dark.to_string()
            } else if let Some(default) = val.get("default").and_then(|v| v.as_str()) {
                default.to_string()
            } else if let Some(s) = val.as_str() {
                s.to_string()
            } else {
                continue;
            };
            colors.insert(key.clone(), color);
        }
    }

    Some(colors)
}

/// Get matugen colors with caching.
/// Returns a dict of color_name -> hex_value.
/// Returns None if matugen fails (caller should use defaults).
#[pyfunction]
fn get_cached_colors(py: Python<'_>, wallpaper_path: &str) -> PyResult<Option<PyObject>> {
    // Try cache first
    if let Some(colors) = load_cache(wallpaper_path) {
        let dict = PyDict::new(py);
        for (k, v) in colors {
            dict.set_item(k, v)?;
        }
        return Ok(Some(dict.into()));
    }

    // Run matugen
    let colors = match run_matugen(wallpaper_path) {
        Some(c) => c,
        None => return Ok(None),
    };

    // Save to cache
    let _ = save_cache(wallpaper_path, &colors);

    // Return as Python dict
    let dict = PyDict::new(py);
    for (k, v) in colors {
        dict.set_item(k, v)?;
    }
    Ok(Some(dict.into()))
}

/// Invalidate the color cache.
#[pyfunction]
fn invalidate_color_cache() -> PyResult<()> {
    if let Some(cache_path) = get_cache_path() {
        let _ = fs::remove_file(cache_path);
    }
    Ok(())
}

// ============================================================================
// PipeWire sinks via wpctl status (fast text parsing)
// ============================================================================

#[derive(Debug, Clone)]
#[pyclass]
struct AudioSink {
    #[pyo3(get)]
    id: u32,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    description: String,
    #[pyo3(get)]
    volume: Option<f64>,
    #[pyo3(get)]
    is_default: bool,
}

#[pymethods]
impl AudioSink {
    fn __repr__(&self) -> String {
        format!(
            "AudioSink(id={}, name={:?}, is_default={})",
            self.id, self.name, self.is_default
        )
    }
}

/// Parse a sink line from wpctl status output.
/// Format: " │  *   34. HyperX Cloud Alpha... [vol: 0.60]"
fn parse_sink_line(line: &str) -> Option<AudioSink> {
    let is_default = line.contains('*');

    // Remove tree chars and asterisk, find the ID
    let cleaned: String = line
        .chars()
        .skip_while(|c| !c.is_ascii_digit())
        .collect();

    // Parse "34. Name [vol: 0.60]"
    let dot_pos = cleaned.find('.')?;
    let id: u32 = cleaned[..dot_pos].trim().parse().ok()?;

    let rest = cleaned[dot_pos + 1..].trim();

    // Extract volume if present
    let (name, volume) = if let Some(vol_start) = rest.find("[vol:") {
        let name = rest[..vol_start].trim();
        let vol_str = &rest[vol_start + 5..];
        let vol_end = vol_str.find(']').unwrap_or(vol_str.len());
        let volume: Option<f64> = vol_str[..vol_end].trim().parse().ok();
        (name, volume)
    } else {
        (rest, None)
    };

    Some(AudioSink {
        id,
        name: name.to_string(),
        description: String::new(),
        volume,
        is_default,
    })
}

/// Get audio sinks from PipeWire via wpctl status.
/// Fast: single subprocess + efficient text parsing.
#[pyfunction]
fn get_audio_sinks() -> PyResult<Vec<AudioSink>> {
    let output = Command::new("wpctl")
        .arg("status")
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    if !output.status.success() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "wpctl status failed",
        ));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);

    // Find Sinks section and parse
    let mut in_sinks = false;
    let mut sinks = Vec::new();

    for line in stdout.lines() {
        if line.contains("Sinks:") {
            in_sinks = true;
            continue;
        }
        if in_sinks && (line.contains("Sources:") || line.contains("Streams:") || line.contains("Filters:")) {
            break;
        }
        if in_sinks {
            if let Some(sink) = parse_sink_line(line) {
                sinks.push(sink);
            }
        }
    }

    Ok(sinks)
}

/// Set the default audio sink by ID.
#[pyfunction]
fn set_default_sink(sink_id: u32) -> PyResult<bool> {
    let output = Command::new("wpctl")
        .args(["set-default", &sink_id.to_string()])
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    Ok(output.status.success())
}

// ============================================================================
// System info
// ============================================================================

/// Get system memory info: (total_bytes, used_bytes, available_bytes)
#[pyfunction]
fn memory_info() -> PyResult<(u64, u64, u64)> {
    use sysinfo::System;
    let sys = System::new_all();
    let total = sys.total_memory();
    let used = sys.used_memory();
    let available = sys.available_memory();
    Ok((total, used, available))
}

/// Get CPU usage as percentage (0.0 - 100.0)
#[pyfunction]
fn cpu_usage() -> PyResult<f32> {
    use sysinfo::System;
    let mut sys = System::new();
    sys.refresh_cpu_usage();
    std::thread::sleep(std::time::Duration::from_millis(100));
    sys.refresh_cpu_usage();
    let usage: f32 =
        sys.cpus().iter().map(|c| c.cpu_usage()).sum::<f32>() / sys.cpus().len() as f32;
    Ok(usage)
}

// ============================================================================
// Python module
// ============================================================================

#[pymodule]
fn wrp_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Command execution
    m.add_function(wrap_pyfunction!(run_command, m)?)?;

    // Hyprland
    m.add_function(wrap_pyfunction!(hyprctl, m)?)?;
    m.add_function(wrap_pyfunction!(hyprctl_json, m)?)?;

    // Colors
    m.add_function(wrap_pyfunction!(get_cached_colors, m)?)?;
    m.add_function(wrap_pyfunction!(invalidate_color_cache, m)?)?;

    // Audio
    m.add_class::<AudioSink>()?;
    m.add_function(wrap_pyfunction!(get_audio_sinks, m)?)?;
    m.add_function(wrap_pyfunction!(set_default_sink, m)?)?;

    // System info
    m.add_function(wrap_pyfunction!(memory_info, m)?)?;
    m.add_function(wrap_pyfunction!(cpu_usage, m)?)?;

    Ok(())
}
