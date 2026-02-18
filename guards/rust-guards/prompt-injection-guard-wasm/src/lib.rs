//! Prompt Injection Guard - WASM Component (Rust)
//!
//! Scans tool call arguments and server responses for prompt injection attacks.
//! Complements the native tool_poisoning guard which only scans tool descriptions.
//!
//! Detection phases:
//! - tool_invoke: Scans tool arguments for injection patterns
//! - response: Scans MCP server responses for indirect prompt injection

mod config;
mod patterns;
mod schema;
mod scoring;

struct PromptInjectionGuard;

wit_bindgen::generate!({
    world: "security-guard",
    path: "wit",
    exports: {
        "mcp:security-guard/guard": PromptInjectionGuard,
    },
});

use exports::mcp::security_guard::guard::{Decision, DenyReason, Guest, GuardContext, Tool};

impl Guest for PromptInjectionGuard {
    fn evaluate_server_connection(_context: GuardContext) -> Result<Decision, String> {
        // Not relevant for prompt injection detection
        Ok(Decision::Allow)
    }

    fn evaluate_tools_list(_tools: Vec<Tool>, _context: GuardContext) -> Result<Decision, String> {
        // Handled by native tool_poisoning guard
        Ok(Decision::Allow)
    }

    fn evaluate_tool_invoke(
        tool_name: String,
        arguments: String,
        context: GuardContext,
    ) -> Result<Decision, String> {
        let cfg = config::get_config();

        if !cfg.scan_tool_arguments {
            return Ok(Decision::Allow);
        }

        // Parse arguments JSON and extract all string content
        let text = match serde_json::from_str::<serde_json::Value>(&arguments) {
            Ok(val) => scoring::extract_text_from_json(&val),
            Err(_) => arguments.clone(),
        };

        if text.is_empty() {
            return Ok(Decision::Allow);
        }

        let result = scoring::scan_text(
            &text,
            &cfg.enabled_categories,
            &cfg.custom_patterns,
            cfg.max_scan_length,
        );

        if result.total_score >= cfg.score_threshold {
            let match_details: Vec<serde_json::Value> = result
                .matches
                .iter()
                .map(|m| {
                    serde_json::json!({
                        "category": m.category,
                        "matched_text": m.matched_text,
                        "weight": m.weight,
                    })
                })
                .collect();

            log_warn(&format!(
                "Prompt injection detected in tool arguments: tool={}, server={}, score={}, threshold={}",
                tool_name, context.server_name, result.total_score, cfg.score_threshold
            ));

            return Ok(Decision::Deny(DenyReason {
                code: "prompt_injection_detected".to_string(),
                message: format!(
                    "Prompt injection detected in tool '{}' arguments (score: {}/{})",
                    tool_name, result.total_score, cfg.score_threshold
                ),
                details: Some(
                    serde_json::json!({
                        "phase": "tool_invoke",
                        "tool_name": tool_name,
                        "server_name": context.server_name,
                        "total_score": result.total_score,
                        "threshold": cfg.score_threshold,
                        "matches": match_details,
                    })
                    .to_string(),
                ),
            }));
        }

        if !result.matches.is_empty() {
            let warnings: Vec<String> = result
                .matches
                .iter()
                .map(|m| {
                    format!(
                        "Suspicious pattern in tool '{}' args: category={}, weight={}",
                        tool_name, m.category, m.weight
                    )
                })
                .collect();
            return Ok(Decision::Warn(warnings));
        }

        Ok(Decision::Allow)
    }

    fn evaluate_response(
        response: String,
        context: GuardContext,
    ) -> Result<Decision, String> {
        let cfg = config::get_config();

        if !cfg.scan_responses {
            return Ok(Decision::Allow);
        }

        // Parse response JSON and extract all string content
        let text = match serde_json::from_str::<serde_json::Value>(&response) {
            Ok(val) => scoring::extract_text_from_json(&val),
            Err(_) => response.clone(),
        };

        if text.is_empty() {
            return Ok(Decision::Allow);
        }

        let result = scoring::scan_text(
            &text,
            &cfg.enabled_categories,
            &cfg.custom_patterns,
            cfg.max_scan_length,
        );

        if result.total_score >= cfg.score_threshold {
            let match_details: Vec<serde_json::Value> = result
                .matches
                .iter()
                .map(|m| {
                    serde_json::json!({
                        "category": m.category,
                        "matched_text": m.matched_text,
                        "weight": m.weight,
                    })
                })
                .collect();

            log_warn(&format!(
                "Prompt injection detected in response: server={}, score={}, threshold={}",
                context.server_name, result.total_score, cfg.score_threshold
            ));

            return Ok(Decision::Deny(DenyReason {
                code: "prompt_injection_in_response".to_string(),
                message: format!(
                    "Prompt injection detected in response from server '{}' (score: {}/{})",
                    context.server_name, result.total_score, cfg.score_threshold
                ),
                details: Some(
                    serde_json::json!({
                        "phase": "response",
                        "server_name": context.server_name,
                        "total_score": result.total_score,
                        "threshold": cfg.score_threshold,
                        "matches": match_details,
                    })
                    .to_string(),
                ),
            }));
        }

        if !result.matches.is_empty() {
            let warnings: Vec<String> = result
                .matches
                .iter()
                .map(|m| {
                    format!(
                        "Suspicious pattern in response from '{}': category={}, weight={}",
                        context.server_name, m.category, m.weight
                    )
                })
                .collect();
            return Ok(Decision::Warn(warnings));
        }

        Ok(Decision::Allow)
    }

    fn get_settings_schema() -> String {
        schema::get_settings_schema()
    }

    fn get_default_config() -> String {
        schema::get_default_config()
    }
}

fn log_warn(msg: &str) {
    mcp::security_guard::host::log(3, msg);
}
