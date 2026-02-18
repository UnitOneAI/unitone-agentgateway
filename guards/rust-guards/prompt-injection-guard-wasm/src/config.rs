//! Configuration parsing for the prompt injection guard.

/// Guard configuration.
#[derive(Debug, Clone)]
pub struct PromptInjectionConfig {
    /// Which pattern categories to enable.
    pub enabled_categories: Vec<String>,
    /// Total risk score threshold to trigger Deny.
    pub score_threshold: u32,
    /// Custom patterns: (substring_pattern, weight).
    pub custom_patterns: Vec<(String, u32)>,
    /// Whether to scan tool invocation arguments.
    pub scan_tool_arguments: bool,
    /// Whether to scan server responses.
    pub scan_responses: bool,
    /// Maximum text length to scan (prevents DoS on large payloads).
    pub max_scan_length: usize,
}

impl Default for PromptInjectionConfig {
    fn default() -> Self {
        Self {
            enabled_categories: vec![
                "prompt_override".to_string(),
                "role_manipulation".to_string(),
                "system_override".to_string(),
                "safety_bypass".to_string(),
                "hidden_instructions".to_string(),
                "data_exfiltration".to_string(),
                "encoding_tricks".to_string(),
            ],
            score_threshold: 5,
            custom_patterns: vec![],
            scan_tool_arguments: true,
            scan_responses: true,
            max_scan_length: 10000,
        }
    }
}

/// Config keys to request from the host.
const CONFIG_KEYS: &[&str] = &[
    "score_threshold",
    "scan_tool_arguments",
    "scan_responses",
    "enabled_categories",
    "max_scan_length",
    "custom_patterns",
];

/// Load and parse configuration from host.
///
/// The host stores config as individual key-value pairs (not a single JSON blob),
/// so we request each key separately and assemble them into a JSON object.
/// Config is read fresh on every call to support hot-reload.
pub fn get_config() -> PromptInjectionConfig {
    // Request each config key individually from the host
    let mut config_map = serde_json::Map::new();
    for &key in CONFIG_KEYS {
        let value_str = crate::mcp::security_guard::host::get_config(key);
        if !value_str.is_empty() {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&value_str) {
                config_map.insert(key.to_string(), parsed);
            }
        }
    }

    if config_map.is_empty() {
        return PromptInjectionConfig::default();
    }

    let val = serde_json::Value::Object(config_map);
    parse_config(&val)
}

fn parse_config(val: &serde_json::Value) -> PromptInjectionConfig {
    let default = PromptInjectionConfig::default();

    let enabled_categories = val
        .get("enabled_categories")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or(default.enabled_categories);

    let score_threshold = val
        .get("score_threshold")
        .and_then(|v| v.as_u64())
        .map(|v| v as u32)
        .unwrap_or(default.score_threshold);

    let custom_patterns = val
        .get("custom_patterns")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|item| {
                    let pattern = item.get("pattern")?.as_str()?.to_string();
                    let weight = item.get("weight").and_then(|w| w.as_u64()).unwrap_or(5) as u32;
                    Some((pattern, weight))
                })
                .collect()
        })
        .unwrap_or(default.custom_patterns);

    let scan_tool_arguments = val
        .get("scan_tool_arguments")
        .and_then(|v| v.as_bool())
        .unwrap_or(default.scan_tool_arguments);

    let scan_responses = val
        .get("scan_responses")
        .and_then(|v| v.as_bool())
        .unwrap_or(default.scan_responses);

    let max_scan_length = val
        .get("max_scan_length")
        .and_then(|v| v.as_u64())
        .map(|v| v as usize)
        .unwrap_or(default.max_scan_length);

    PromptInjectionConfig {
        enabled_categories,
        score_threshold,
        custom_patterns,
        scan_tool_arguments,
        scan_responses,
        max_scan_length,
    }
}
