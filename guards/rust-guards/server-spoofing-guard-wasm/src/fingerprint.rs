use sha2::{Digest, Sha256};

use crate::exports::mcp::security_guard::guard::Tool;

/// Compute a fingerprint for a tool based on its metadata.
///
/// Format: SHA256("{name}|{description}|{input_schema}"), first 16 hex chars.
/// Matches Python `_compute_tool_fingerprint` from `app.py`.
pub fn compute_tool_fingerprint(tool: &Tool) -> String {
    let desc = tool.description.as_deref().unwrap_or("");
    let content = format!("{}|{}|{}", tool.name, desc, tool.input_schema);

    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    let result = hasher.finalize();

    // First 8 bytes = 16 hex characters, matching Python hexdigest()[:16]
    hex::encode(&result[..8])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_tool(name: &str, description: Option<&str>, schema: &str) -> Tool {
        Tool {
            name: name.to_string(),
            description: description.map(|s| s.to_string()),
            input_schema: schema.to_string(),
        }
    }

    #[test]
    fn test_fingerprint_is_16_hex_chars() {
        let tool = make_tool("test-tool", Some("A test tool"), "{}");
        let fp = compute_tool_fingerprint(&tool);
        assert_eq!(fp.len(), 16);
        assert!(fp.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_fingerprint_deterministic() {
        let tool = make_tool("test-tool", Some("A test tool"), "{}");
        let fp1 = compute_tool_fingerprint(&tool);
        let fp2 = compute_tool_fingerprint(&tool);
        assert_eq!(fp1, fp2);
    }

    #[test]
    fn test_fingerprint_different_tools() {
        let tool_a = make_tool("tool-a", Some("Description A"), "{}");
        let tool_b = make_tool("tool-b", Some("Description B"), "{}");
        let fp_a = compute_tool_fingerprint(&tool_a);
        let fp_b = compute_tool_fingerprint(&tool_b);
        assert_ne!(fp_a, fp_b);
    }

    #[test]
    fn test_fingerprint_none_description() {
        let tool = make_tool("test-tool", None, "{}");
        let fp = compute_tool_fingerprint(&tool);
        assert_eq!(fp.len(), 16);
        // None description should produce same as empty string description
        let tool_empty = make_tool("test-tool", Some(""), "{}");
        let fp_empty = compute_tool_fingerprint(&tool_empty);
        assert_eq!(fp, fp_empty);
    }
}
