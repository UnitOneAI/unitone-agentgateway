/// Returns JSON Schema describing the guard's configurable parameters.
/// Matches the Python WASM guard's `get_settings_schema` output exactly.
pub fn get_settings_schema() -> String {
    serde_json::json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "agentgateway://guards/server-spoofing/v1",
        "title": "Server Spoofing Guard",
        "description": "Detects and blocks server spoofing attacks including fake servers, typosquatting, and tool mimicry",
        "type": "object",
        "properties": {
            "whitelist_enabled": {
                "type": "boolean",
                "title": "Enable Whitelist",
                "description": "Enable server whitelist checking. When disabled, all servers are allowed.",
                "default": true,
                "x-ui": {
                    "component": "checkbox",
                    "order": 1,
                    "group": "whitelist"
                }
            },
            "whitelist": {
                "type": "array",
                "title": "Approved Servers",
                "description": "List of approved MCP servers with optional URL patterns and tool fingerprints",
                "default": [],
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "title": "Server Name",
                            "description": "Exact server name to whitelist"
                        },
                        "url_pattern": {
                            "type": "string",
                            "title": "URL Pattern",
                            "description": "Regex pattern to match server URL (optional)",
                            "format": "regex"
                        },
                        "tool_fingerprints": {
                            "type": "object",
                            "title": "Tool Fingerprints",
                            "description": "Map of tool name to expected fingerprint hash for mimicry detection",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["name"]
                },
                "x-ui": {
                    "component": "object-array",
                    "placeholder": "Add approved server",
                    "helpText": "Each entry defines an approved server. Tool fingerprints are used for mimicry detection.",
                    "order": 2,
                    "group": "whitelist"
                }
            },
            "block_unknown_servers": {
                "type": "boolean",
                "title": "Block Unknown Servers",
                "description": "Deny connections from servers not in the whitelist. When disabled, unknown servers generate warnings instead.",
                "default": true,
                "x-ui": {
                    "component": "checkbox",
                    "helpText": "If disabled, unrecognized servers will be allowed with a warning",
                    "order": 3,
                    "group": "whitelist"
                }
            },
            "typosquat_detection_enabled": {
                "type": "boolean",
                "title": "Enable Typosquat Detection",
                "description": "Detect server names that are suspiciously similar to approved servers (e.g., 'finance-too1s' vs 'finance-tools')",
                "default": true,
                "x-ui": {
                    "component": "checkbox",
                    "order": 4,
                    "group": "typosquat"
                }
            },
            "typosquat_similarity_threshold": {
                "type": "number",
                "title": "Similarity Threshold",
                "description": "Levenshtein similarity ratio (0.0-1.0) above which a server name is flagged as a potential typosquat. Higher values are stricter.",
                "default": 0.85,
                "minimum": 0.0,
                "maximum": 1.0,
                "x-ui": {
                    "component": "slider",
                    "helpText": "0.85 means names must be 85% similar to trigger detection. Lower values catch more but may produce false positives.",
                    "order": 5,
                    "group": "typosquat"
                }
            },
            "tool_mimicry_detection_enabled": {
                "type": "boolean",
                "title": "Enable Tool Mimicry Detection",
                "description": "Detect when an untrusted server provides tools that match fingerprints or names of tools from trusted servers",
                "default": true,
                "x-ui": {
                    "component": "checkbox",
                    "helpText": "Compares tool fingerprints (SHA-256 of name+description+schema) and tool names across servers",
                    "order": 6,
                    "group": "mimicry"
                }
            }
        },
        "x-ui-groups": {
            "whitelist": {
                "title": "Server Whitelist",
                "order": 1,
                "description": "Control which MCP servers are allowed to connect"
            },
            "typosquat": {
                "title": "Typosquat Detection",
                "order": 2,
                "description": "Detect servers with names similar to approved servers"
            },
            "mimicry": {
                "title": "Tool Mimicry Detection",
                "order": 3,
                "description": "Detect tools that impersonate tools from trusted servers"
            }
        },
        "x-guard-meta": {
            "guardType": "server_spoofing",
            "version": "1.0.0",
            "category": "detection",
            "defaultRunsOn": ["connection", "tools_list"],
            "icon": "shield-alert"
        }
    })
    .to_string()
}

/// Returns default configuration as JSON.
/// Matches the Python WASM guard's `get_default_config` output exactly.
pub fn get_default_config() -> String {
    serde_json::json!({
        "whitelist_enabled": true,
        "whitelist": [],
        "block_unknown_servers": true,
        "typosquat_detection_enabled": true,
        "typosquat_similarity_threshold": 0.85,
        "tool_mimicry_detection_enabled": true
    })
    .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settings_schema_is_valid_json() {
        let schema_str = get_settings_schema();
        let val: serde_json::Value = serde_json::from_str(&schema_str).unwrap();
        assert!(val.is_object());
    }

    #[test]
    fn test_settings_schema_has_required_fields() {
        let schema_str = get_settings_schema();
        let val: serde_json::Value = serde_json::from_str(&schema_str).unwrap();

        assert!(val.get("$schema").is_some());
        assert!(val.get("$id").is_some());
        assert!(val.get("title").is_some());
        assert!(val.get("properties").is_some());
        assert!(val.get("x-guard-meta").is_some());

        let meta = val.get("x-guard-meta").unwrap();
        assert_eq!(meta.get("guardType").unwrap(), "server_spoofing");
    }

    #[test]
    fn test_settings_schema_has_all_config_properties() {
        let schema_str = get_settings_schema();
        let val: serde_json::Value = serde_json::from_str(&schema_str).unwrap();
        let props = val.get("properties").unwrap();

        let expected = [
            "whitelist_enabled",
            "whitelist",
            "block_unknown_servers",
            "typosquat_detection_enabled",
            "typosquat_similarity_threshold",
            "tool_mimicry_detection_enabled",
        ];
        for key in expected {
            assert!(props.get(key).is_some(), "Missing property: {}", key);
        }
    }

    #[test]
    fn test_settings_schema_has_ui_groups() {
        let schema_str = get_settings_schema();
        let val: serde_json::Value = serde_json::from_str(&schema_str).unwrap();
        let groups = val.get("x-ui-groups").unwrap();

        assert!(groups.get("whitelist").is_some());
        assert!(groups.get("typosquat").is_some());
        assert!(groups.get("mimicry").is_some());
    }

    #[test]
    fn test_default_config_is_valid_json() {
        let config_str = get_default_config();
        let val: serde_json::Value = serde_json::from_str(&config_str).unwrap();
        assert!(val.is_object());
    }

    #[test]
    fn test_default_config_has_all_keys() {
        let config_str = get_default_config();
        let val: serde_json::Value = serde_json::from_str(&config_str).unwrap();

        assert_eq!(val.get("whitelist_enabled").unwrap(), true);
        assert_eq!(val.get("block_unknown_servers").unwrap(), true);
        assert_eq!(val.get("typosquat_detection_enabled").unwrap(), true);
        assert_eq!(val.get("typosquat_similarity_threshold").unwrap(), 0.85);
        assert_eq!(val.get("tool_mimicry_detection_enabled").unwrap(), true);
        assert!(val.get("whitelist").unwrap().is_array());
    }

    #[test]
    fn test_schema_and_config_consistency() {
        let schema_str = get_settings_schema();
        let schema: serde_json::Value = serde_json::from_str(&schema_str).unwrap();
        let schema_props = schema.get("properties").unwrap().as_object().unwrap();

        let config_str = get_default_config();
        let config: serde_json::Value = serde_json::from_str(&config_str).unwrap();
        let config_obj = config.as_object().unwrap();

        for key in config_obj.keys() {
            assert!(
                schema_props.contains_key(key),
                "Config key '{}' not found in schema properties",
                key
            );
        }
    }
}
