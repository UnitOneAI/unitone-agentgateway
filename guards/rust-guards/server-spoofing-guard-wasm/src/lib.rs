//! Server Spoofing Guard - WASM Component (Rust)
//!
//! Protects against:
//! 1. Fake servers not in whitelist
//! 2. Typosquatting attacks (e.g., "company-to0ls" vs "company-tools")
//! 3. Tool mimicry (malicious server copying trusted server's tools)
//! 4. Tool namespace collisions across servers

mod config;
mod fingerprint;
mod levenshtein;
mod mimicry;
mod schema;
mod state;
mod typosquat;

struct ServerSpoofingGuard;

wit_bindgen::generate!({
    world: "security-guard",
    path: "wit",
    exports: {
        "mcp:security-guard/guard": ServerSpoofingGuard,
    },
});

use exports::mcp::security_guard::guard::{Decision, DenyReason, Guest, GuardContext, Tool};

impl Guest for ServerSpoofingGuard {
    fn evaluate_server_connection(context: GuardContext) -> Result<Decision, String> {
        let server_name = &context.server_name;
        let cfg = config::get_config();

        log_debug(&format!("Evaluating server connection: {}", server_name));

        // Check if whitelisting is enabled
        if !cfg.whitelist_enabled {
            return Ok(Decision::Allow);
        }

        // Check whitelist
        if config::is_whitelisted(server_name) {
            log_debug(&format!("Server '{}' is whitelisted", server_name));
            return Ok(Decision::Allow);
        }

        // Check for typosquat
        if cfg.typosquat_detection_enabled {
            if let Some(typosquat_match) = typosquat::detect_typosquat(server_name) {
                log_warn(&format!(
                    "Typosquat detected: '{}' similar to '{}'",
                    server_name, typosquat_match
                ));
                return Ok(Decision::Deny(DenyReason {
                    code: "typosquat_detected".to_string(),
                    message: format!(
                        "Server '{}' appears to be typosquatting approved server '{}'",
                        server_name, typosquat_match
                    ),
                    details: Some(
                        serde_json::json!({
                            "detected_name": server_name,
                            "similar_to": typosquat_match,
                            "attack_type": "typosquatting",
                        })
                        .to_string(),
                    ),
                }));
            }
        }

        // Block unknown servers if configured
        if cfg.block_unknown_servers {
            log_warn(&format!("Blocking unknown server: {}", server_name));
            return Ok(Decision::Deny(DenyReason {
                code: "server_not_whitelisted".to_string(),
                message: format!(
                    "Server '{}' is not in the approved server registry",
                    server_name
                ),
                details: Some(
                    serde_json::json!({
                        "server_name": server_name,
                        "action": "Add server to whitelist if this is a legitimate server",
                    })
                    .to_string(),
                ),
            }));
        }

        // Warn but allow
        log_info(&format!(
            "Warning: Server '{}' is not in whitelist",
            server_name
        ));
        Ok(Decision::Warn(vec![format!(
            "Server '{}' is not in whitelist",
            server_name
        )]))
    }

    fn evaluate_tools_list(tools: Vec<Tool>, context: GuardContext) -> Result<Decision, String> {
        let server_name = &context.server_name;
        let cfg = config::get_config();

        log_debug(&format!(
            "Evaluating {} tools from server: {}",
            tools.len(),
            server_name
        ));

        // Check for tool mimicry
        if cfg.tool_mimicry_detection_enabled {
            if let Some(mimicry_info) = mimicry::check_tool_mimicry(server_name, &tools) {
                log_warn(&format!("Tool mimicry detected: {}", mimicry_info));
                return Ok(Decision::Deny(DenyReason {
                    code: "tool_mimicry_detected".to_string(),
                    message: format!(
                        "Server '{}' contains tools that mimic trusted server tools",
                        server_name
                    ),
                    details: Some(
                        serde_json::json!({
                            "server_name": server_name,
                            "mimicked_tools": [mimicry_info],
                            "attack_type": "tool_mimicry",
                        })
                        .to_string(),
                    ),
                }));
            }
        }

        // Check for namespace collisions
        if let Some(collision_info) = mimicry::check_namespace_collision(server_name, &tools) {
            log_warn(&format!("Tool namespace collision: {}", collision_info));
            return Ok(Decision::Deny(DenyReason {
                code: "tool_namespace_collision".to_string(),
                message: format!(
                    "Server '{}' has tools that collide with other servers",
                    server_name
                ),
                details: Some(
                    serde_json::json!({
                        "collisions": [collision_info],
                        "recommendation": "Use namespaced tool names (e.g., server_name.tool_name)",
                    })
                    .to_string(),
                ),
            }));
        }

        // Register tools for this server
        let tool_fingerprints: std::collections::HashMap<String, String> = tools
            .iter()
            .map(|tool| {
                let fp = fingerprint::compute_tool_fingerprint(tool);
                (tool.name.clone(), fp)
            })
            .collect();

        state::update_tool_registry(|registry| {
            registry.insert(server_name.clone(), tool_fingerprints);
        });

        log_debug(&format!(
            "Registered {} tools for server: {}",
            tools.len(),
            server_name
        ));
        Ok(Decision::Allow)
    }

    fn evaluate_tool_invoke(
        _tool_name: String,
        _arguments: String,
        _context: GuardContext,
    ) -> Result<Decision, String> {
        Ok(Decision::Allow)
    }

    fn evaluate_response(
        _response: String,
        _context: GuardContext,
    ) -> Result<Decision, String> {
        Ok(Decision::Allow)
    }

    fn get_settings_schema() -> String {
        schema::get_settings_schema()
    }

    fn get_default_config() -> String {
        schema::get_default_config()
    }
}

// Logging helpers using host functions
#[allow(dead_code)]
fn log_debug(msg: &str) {
    mcp::security_guard::host::log(1, msg);
}

fn log_info(msg: &str) {
    mcp::security_guard::host::log(2, msg);
}

fn log_warn(msg: &str) {
    mcp::security_guard::host::log(3, msg);
}

fn log_error(msg: &str) {
    mcp::security_guard::host::log(4, msg);
}
