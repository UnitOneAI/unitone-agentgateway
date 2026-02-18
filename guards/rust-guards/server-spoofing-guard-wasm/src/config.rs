use std::collections::HashMap;

/// A whitelist entry from configuration.
#[derive(Debug, Clone)]
pub struct WhitelistEntry {
    pub name: String,
    pub url_pattern: Option<String>,
    pub tool_fingerprints: HashMap<String, String>,
}

/// Parsed guard configuration with all 6 fields.
#[derive(Debug, Clone)]
pub struct GuardConfig {
    pub whitelist_enabled: bool,
    pub whitelist: Vec<WhitelistEntry>,
    pub block_unknown_servers: bool,
    pub typosquat_detection_enabled: bool,
    pub typosquat_similarity_threshold: f64,
    pub tool_mimicry_detection_enabled: bool,
}

impl Default for GuardConfig {
    fn default() -> Self {
        GuardConfig {
            whitelist_enabled: true,
            whitelist: vec![],
            block_unknown_servers: true,
            typosquat_detection_enabled: true,
            typosquat_similarity_threshold: 0.85,
            tool_mimicry_detection_enabled: true,
        }
    }
}

/// Config keys to request from the host.
const CONFIG_KEYS: &[&str] = &[
    "whitelist_enabled",
    "whitelist",
    "block_unknown_servers",
    "typosquat_detection_enabled",
    "typosquat_similarity_threshold",
    "tool_mimicry_detection_enabled",
];

/// Load configuration from host.
///
/// The host stores config as individual key-value pairs (not a single JSON blob),
/// so we request each key separately and assemble them into a JSON object.
/// Config is read fresh on every call to support hot-reload.
pub fn get_config() -> GuardConfig {
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
        return GuardConfig::default();
    }

    let val = serde_json::Value::Object(config_map);
    parse_config(&val)
}

/// Get whitelist entries from config.
pub fn get_whitelist() -> Vec<WhitelistEntry> {
    get_config().whitelist
}

/// Get typosquat similarity threshold from config.
pub fn get_threshold() -> f64 {
    get_config().typosquat_similarity_threshold
}

/// Check if a server name is in the whitelist (case-insensitive).
pub fn is_whitelisted(server_name: &str) -> bool {
    let whitelist = get_whitelist();
    let server_lower = server_name.to_lowercase();
    whitelist
        .iter()
        .any(|entry| entry.name.to_lowercase() == server_lower)
}

fn parse_config(val: &serde_json::Value) -> GuardConfig {
    let whitelist_enabled = val
        .get("whitelist_enabled")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);

    let block_unknown_servers = val
        .get("block_unknown_servers")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);

    let typosquat_detection_enabled = val
        .get("typosquat_detection_enabled")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);

    let typosquat_similarity_threshold = val
        .get("typosquat_similarity_threshold")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.85);

    let tool_mimicry_detection_enabled = val
        .get("tool_mimicry_detection_enabled")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);

    let whitelist = val
        .get("whitelist")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|entry| {
                    let name = entry.get("name")?.as_str()?.to_string();
                    let url_pattern = entry
                        .get("url_pattern")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());
                    let tool_fingerprints = entry
                        .get("tool_fingerprints")
                        .and_then(|v| v.as_object())
                        .map(|obj| {
                            obj.iter()
                                .filter_map(|(k, v)| Some((k.clone(), v.as_str()?.to_string())))
                                .collect()
                        })
                        .unwrap_or_default();
                    Some(WhitelistEntry {
                        name,
                        url_pattern,
                        tool_fingerprints,
                    })
                })
                .collect()
        })
        .unwrap_or_default();

    GuardConfig {
        whitelist_enabled,
        whitelist,
        block_unknown_servers,
        typosquat_detection_enabled,
        typosquat_similarity_threshold,
        tool_mimicry_detection_enabled,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = GuardConfig::default();
        assert!(config.whitelist_enabled);
        assert!(config.block_unknown_servers);
        assert!(config.typosquat_detection_enabled);
        assert!((config.typosquat_similarity_threshold - 0.85).abs() < f64::EPSILON);
        assert!(config.tool_mimicry_detection_enabled);
        assert!(config.whitelist.is_empty());
    }

    #[test]
    fn test_parse_empty_config() {
        let val = serde_json::json!({});
        let config = parse_config(&val);
        assert!(config.whitelist_enabled);
        assert!(config.block_unknown_servers);
        assert!(config.whitelist.is_empty());
    }

    #[test]
    fn test_parse_full_config() {
        let val = serde_json::json!({
            "whitelist_enabled": false,
            "whitelist": [
                {
                    "name": "test-server",
                    "url_pattern": "https://test\\.example\\.com/.*",
                    "tool_fingerprints": {
                        "my-tool": "abc123"
                    }
                }
            ],
            "block_unknown_servers": false,
            "typosquat_detection_enabled": false,
            "typosquat_similarity_threshold": 0.9,
            "tool_mimicry_detection_enabled": false
        });
        let config = parse_config(&val);
        assert!(!config.whitelist_enabled);
        assert!(!config.block_unknown_servers);
        assert!(!config.typosquat_detection_enabled);
        assert!((config.typosquat_similarity_threshold - 0.9).abs() < f64::EPSILON);
        assert!(!config.tool_mimicry_detection_enabled);
        assert_eq!(config.whitelist.len(), 1);
        assert_eq!(config.whitelist[0].name, "test-server");
        assert_eq!(
            config.whitelist[0].url_pattern.as_deref(),
            Some("https://test\\.example\\.com/.*")
        );
        assert_eq!(
            config.whitelist[0].tool_fingerprints.get("my-tool"),
            Some(&"abc123".to_string())
        );
    }

    #[test]
    fn test_parse_whitelist_missing_name() {
        let val = serde_json::json!({
            "whitelist": [
                { "url_pattern": "https://test.com" }
            ]
        });
        let config = parse_config(&val);
        // Entry without "name" is filtered out
        assert!(config.whitelist.is_empty());
    }
}
