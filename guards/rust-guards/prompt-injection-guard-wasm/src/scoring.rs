//! Risk scoring engine for prompt injection detection.
//!
//! Scans text against enabled pattern categories and computes
//! a total risk score. If score >= threshold, returns Deny.

use crate::patterns::{self, PatternMatch};

/// Result of scanning text for injection patterns.
pub struct ScanResult {
    pub total_score: u32,
    pub matches: Vec<PatternMatch>,
}

/// Scan text against all enabled pattern categories.
pub fn scan_text(
    text: &str,
    enabled_categories: &[String],
    custom_patterns: &[(String, u32)],
    max_scan_length: usize,
) -> ScanResult {
    let mut matches = Vec::new();
    let mut total_score: u32 = 0;

    // Truncate text if too long
    let scan_text = if text.len() > max_scan_length {
        &text[..max_scan_length]
    } else {
        text
    };

    // Normalize once for all pattern matching
    let normalized = patterns::normalize_text(scan_text);

    // Scan against built-in categories
    for category_name in enabled_categories {
        if let Some(category) = patterns::find_category(category_name) {
            // Check keyword patterns
            for pattern in category.patterns {
                if let Some(matched) = patterns::match_pattern(&normalized, pattern) {
                    matches.push(PatternMatch {
                        category: category.name.to_string(),
                        matched_text: truncate_match(&matched, 100),
                        weight: category.weight,
                    });
                    total_score = total_score.saturating_add(category.weight);
                    // Only count first match per category to avoid score inflation
                    break;
                }
            }

            // Special: check zero-width chars for hidden_instructions category
            if category.name == "hidden_instructions"
                && patterns::has_zero_width_chars(scan_text)
                && !matches.iter().any(|m| m.category == "hidden_instructions")
            {
                matches.push(PatternMatch {
                    category: "hidden_instructions".to_string(),
                    matched_text: "(zero-width characters detected)".to_string(),
                    weight: category.weight,
                });
                total_score = total_score.saturating_add(category.weight);
            }
        }
    }

    // Scan against custom patterns (simple substring matching)
    for (pattern, weight) in custom_patterns {
        if let Some(matched) = patterns::match_custom_pattern(&normalized, pattern) {
            matches.push(PatternMatch {
                category: "custom".to_string(),
                matched_text: truncate_match(&matched, 100),
                weight: *weight,
            });
            total_score = total_score.saturating_add(*weight);
        }
    }

    ScanResult {
        total_score,
        matches,
    }
}

/// Truncate match text for reporting.
fn truncate_match(text: &str, max_len: usize) -> String {
    if text.len() > max_len {
        format!("{}...", &text[..max_len])
    } else {
        text.to_string()
    }
}

/// Scan JSON value recursively and extract all string content.
pub fn extract_text_from_json(value: &serde_json::Value) -> String {
    let mut parts = Vec::new();
    collect_strings(value, &mut parts);
    parts.join(" ")
}

fn collect_strings(value: &serde_json::Value, parts: &mut Vec<String>) {
    match value {
        serde_json::Value::String(s) => {
            parts.push(s.clone());
        }
        serde_json::Value::Array(arr) => {
            for item in arr {
                collect_strings(item, parts);
            }
        }
        serde_json::Value::Object(obj) => {
            for (_key, val) in obj {
                collect_strings(val, parts);
            }
        }
        _ => {}
    }
}
