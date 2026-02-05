use crate::config;
use crate::fingerprint;
use crate::state;

use crate::exports::mcp::security_guard::guard::Tool;

/// Check if tools mimic trusted server tools.
/// Returns `Some(mimicry_info)` if detected.
///
/// Matches Python `_check_tool_mimicry` from `app.py`.
pub fn check_tool_mimicry(server_name: &str, tools: &[Tool]) -> Option<serde_json::Value> {
    let whitelist = config::get_whitelist();
    let server_lower = server_name.to_lowercase();

    for tool in tools {
        for entry in &whitelist {
            let entry_lower = entry.name.to_lowercase();
            if entry_lower == server_lower {
                continue;
            }

            let fp = fingerprint::compute_tool_fingerprint(tool);

            for (trusted_name, trusted_fp) in &entry.tool_fingerprints {
                if fp == *trusted_fp {
                    return Some(serde_json::json!({
                        "tool_name": tool.name,
                        "mimics_server": entry.name,
                        "mimics_tool": trusted_name,
                        "match_type": "exact_fingerprint",
                    }));
                }

                if tool.name.to_lowercase() == trusted_name.to_lowercase() {
                    return Some(serde_json::json!({
                        "tool_name": tool.name,
                        "mimics_server": entry.name,
                        "mimics_tool": trusted_name,
                        "match_type": "name_collision",
                    }));
                }
            }
        }
    }

    None
}

/// Check for tool name collisions with other registered servers.
/// Returns `Some(collision_info)` if detected.
///
/// Matches Python `_check_namespace_collision` from `app.py`.
pub fn check_namespace_collision(server_name: &str, tools: &[Tool]) -> Option<serde_json::Value> {
    let server_lower = server_name.to_lowercase();

    state::get_tool_registry(|registry| {
        for tool in tools {
            for (other_server, other_tools) in registry.iter() {
                if other_server.to_lowercase() == server_lower {
                    continue;
                }

                if other_tools.contains_key(&tool.name) {
                    return Some(serde_json::json!({
                        "tool_name": tool.name,
                        "this_server": server_name,
                        "other_server": other_server,
                    }));
                }
            }
        }
        None
    })
}
