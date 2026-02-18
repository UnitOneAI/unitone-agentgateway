//! JSON Schema definition for guard configuration UI.

/// Returns JSON Schema (Draft 2020-12) with x-ui hints for the UI.
pub fn get_settings_schema() -> String {
    serde_json::json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "agentgateway://guards/prompt-injection/v1",
        "title": "Prompt Injection Guard",
        "description": "Detects and blocks prompt injection attacks in tool arguments and server responses",
        "type": "object",
        "properties": {
            "scan_tool_arguments": {
                "type": "boolean",
                "title": "Scan Tool Arguments",
                "description": "Scan tool call arguments for injection patterns",
                "default": true,
                "x-ui": {
                    "component": "checkbox",
                    "order": 1
                }
            },
            "scan_responses": {
                "type": "boolean",
                "title": "Scan Responses",
                "description": "Scan MCP server responses for indirect prompt injection",
                "default": true,
                "x-ui": {
                    "component": "checkbox",
                    "order": 2
                }
            },
            "enabled_categories": {
                "type": "array",
                "title": "Enabled Pattern Categories",
                "description": "Which attack categories to detect",
                "items": {
                    "type": "string",
                    "enum": [
                        "prompt_override",
                        "role_manipulation",
                        "system_override",
                        "safety_bypass",
                        "hidden_instructions",
                        "data_exfiltration",
                        "encoding_tricks"
                    ]
                },
                "default": [
                    "prompt_override",
                    "role_manipulation",
                    "system_override",
                    "safety_bypass",
                    "hidden_instructions",
                    "data_exfiltration",
                    "encoding_tricks"
                ],
                "x-ui": {
                    "component": "tags",
                    "order": 3
                }
            },
            "score_threshold": {
                "type": "integer",
                "title": "Score Threshold",
                "description": "Minimum risk score to block (weights: system_override=9, prompt_override/safety_bypass=8, role_manipulation/data_exfiltration=7, hidden_instructions=6, encoding_tricks=5)",
                "default": 5,
                "minimum": 1,
                "maximum": 50,
                "x-ui": {
                    "component": "input",
                    "order": 4
                }
            },
            "max_scan_length": {
                "type": "integer",
                "title": "Max Scan Length",
                "description": "Maximum text length to scan (characters). Prevents slowdown on large payloads.",
                "default": 10000,
                "minimum": 100,
                "maximum": 100000,
                "x-ui": {
                    "component": "input",
                    "order": 5
                }
            },
            "custom_patterns": {
                "type": "array",
                "title": "Custom Patterns",
                "description": "Additional substring patterns to detect (case-insensitive)",
                "items": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "title": "Pattern",
                            "description": "Case-insensitive substring to match"
                        },
                        "weight": {
                            "type": "integer",
                            "title": "Weight",
                            "description": "Risk score weight for this pattern",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["pattern"]
                },
                "default": [],
                "x-ui": {
                    "component": "object-array",
                    "placeholder": "Add custom pattern",
                    "order": 6
                }
            }
        },
        "x-guard-meta": {
            "guardType": "prompt_injection",
            "version": "1.0.0",
            "category": "detection",
            "defaultRunsOn": ["tool_invoke", "response"],
            "icon": "shield-alert"
        }
    })
    .to_string()
}

/// Returns default configuration as JSON.
pub fn get_default_config() -> String {
    serde_json::json!({
        "scan_tool_arguments": true,
        "scan_responses": true,
        "enabled_categories": [
            "prompt_override",
            "role_manipulation",
            "system_override",
            "safety_bypass",
            "hidden_instructions",
            "data_exfiltration",
            "encoding_tricks"
        ],
        "score_threshold": 5,
        "max_scan_length": 10000,
        "custom_patterns": []
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
        assert!(val.get("$schema").is_some());
        assert!(val.get("x-guard-meta").is_some());
    }

    #[test]
    fn test_default_config_is_valid_json() {
        let config_str = get_default_config();
        let val: serde_json::Value = serde_json::from_str(&config_str).unwrap();
        assert!(val.is_object());
    }

    #[test]
    fn test_schema_and_config_consistency() {
        let schema_str = get_settings_schema();
        let schema: serde_json::Value = serde_json::from_str(&schema_str).unwrap();
        let schema_props = schema.get("properties").unwrap().as_object().unwrap();

        let config_str = get_default_config();
        let config: serde_json::Value = serde_json::from_str(&config_str).unwrap();
        let config_obj = config.as_object().unwrap();

        // Every config key must be in schema
        for key in config_obj.keys() {
            assert!(
                schema_props.contains_key(key),
                "Config key '{}' not in schema",
                key
            );
        }
    }
}
