use crate::config;
use crate::levenshtein;

/// Detect if server_name is a typosquat of an approved server.
/// Returns `Some(approved_name)` if detected, `None` otherwise.
///
/// Matches Python `_detect_typosquat` from `app.py`.
pub fn detect_typosquat(server_name: &str) -> Option<String> {
    let threshold = config::get_threshold();
    let whitelist = config::get_whitelist();
    let test_name = server_name.to_lowercase();

    for entry in &whitelist {
        let approved_name = entry.name.to_lowercase();

        // Skip exact matches
        if approved_name == test_name {
            continue;
        }

        let similarity = levenshtein::levenshtein_ratio(&approved_name, &test_name);

        if similarity >= threshold && is_typosquat_pattern(&approved_name, &test_name) {
            return Some(entry.name.clone());
        }
    }

    None
}

/// Check for common typosquat patterns: single-char substitution and homoglyphs.
///
/// Matches Python `_is_typosquat_pattern` from `app.py`.
fn is_typosquat_pattern(approved: &str, suspect: &str) -> bool {
    let approved_chars: Vec<char> = approved.chars().collect();
    let suspect_chars: Vec<char> = suspect.chars().collect();

    // Check single character substitution (same length, exactly 1 diff)
    if approved_chars.len() == suspect_chars.len() {
        let diffs = approved_chars
            .iter()
            .zip(suspect_chars.iter())
            .filter(|(a, b)| a != b)
            .count();
        if diffs == 1 {
            return true;
        }
    }

    // Check homoglyph attacks (visually similar characters)
    let normalized = normalize_homoglyphs(suspect);
    if approved == normalized && approved != suspect {
        return true;
    }

    false
}

/// Normalize homoglyphs by replacing visually similar characters.
///
/// Applies replacements in the same order as the Python implementation:
///   'o': ['0'], 'l': ['1', 'I', '|'], 'i': ['1', 'l', '|'], 'a': ['@'], 'e': ['3']
///
/// Note: The Python iteration order causes cascading effects (e.g., 'l' subs happen
/// before 'i' subs, so 'l' -> 'i' replaces ALL 'l' characters including originals).
fn normalize_homoglyphs(s: &str) -> String {
    let mut result = s.to_string();

    // 'o': ['0']
    result = result.replace('0', "o");

    // 'l': ['1', 'I', '|']
    result = result.replace('1', "l");
    result = result.replace('I', "l");
    result = result.replace('|', "l");

    // 'i': ['1', 'l', '|']
    // After the previous step, '1' and '|' are already replaced.
    // But 'l' -> 'i' converts ALL remaining 'l' chars (including originals).
    result = result.replace('1', "i"); // no-op (already replaced above)
    result = result.replace('l', "i"); // converts ALL 'l' to 'i'
    result = result.replace('|', "i"); // no-op (already replaced above)

    // 'a': ['@']
    result = result.replace('@', "a");

    // 'e': ['3']
    result = result.replace('3', "e");

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_typosquat_single_char_substitution() {
        assert!(is_typosquat_pattern("finance-tools", "finance-toals"));
    }

    #[test]
    fn test_is_typosquat_homoglyph_zero_for_o() {
        // "c0mpany-tools" -> after normalization: "company-toois"
        // "company-tools" -> after normalization they should match?
        // Actually, let's trace: normalize("c0mpany-tools"):
        //   '0'->'o': "company-tools"
        //   '1'->'l': "company-tools"
        //   'I'->'l': "company-tools"
        //   '|'->'l': "company-tools"
        //   '1'->'i': "company-tools"
        //   'l'->'i': "company-toois"
        //   '|'->'i': "company-toois"
        //   '@'->'a': "company-toois"
        //   '3'->'e': "company-toois"
        //
        // approved = "company-tools", normalized suspect = "company-toois"
        // These don't match, so homoglyph path returns false.
        //
        // But single-char substitution: "company-tools" vs "c0mpany-tools"
        // Both have 14 chars, diff at position 1 ('o' vs '0'), diffs = 1 -> true
        assert!(is_typosquat_pattern("company-tools", "c0mpany-tools"));
    }

    #[test]
    fn test_is_typosquat_homoglyph_one_for_l() {
        // "finance-tools" vs "finance-too1s"
        // Same length, diff at position 11 ('l' vs '1'), diffs = 1 -> true
        assert!(is_typosquat_pattern("finance-tools", "finance-too1s"));
    }

    #[test]
    fn test_not_typosquat_completely_different() {
        assert!(!is_typosquat_pattern("finance-tools", "weather-api"));
    }

    #[test]
    fn test_normalize_homoglyphs_zero_for_o() {
        let result = normalize_homoglyphs("c0mpany");
        // '0'->'o': "company", then 'l'->'i' converts all 'l' (none here)
        // But wait: 'l'->'i' happens, converting original 'l' in result... no 'l' in "company"
        // Actually there is no 'l' in "company", so result = "company"
        // Hmm but the 'i' step replaces 'l' with 'i'. "company" has no 'l'. So stays "company".
        // Wait, I need to re-trace more carefully.
        //
        // After all steps: "c0mpany" -> "company" (o step) -> no l/I/| changes
        // -> 'l'->'i' but no 'l' exists -> "company" -> no @/3 -> "company"
        //
        // But then normalize_homoglyphs("company") should also convert 'l' to 'i':
        // "company" has no 'l', so it stays "company"
        //
        // So normalize("c0mpany") = "company" ✓
        assert_eq!(result, "company");
    }

    #[test]
    fn test_normalize_homoglyphs_cascading() {
        // Demonstrate the cascading l->i effect
        // "hello" -> '0': "hello" -> '1': "hello" -> 'I': "hello" -> '|': "hello"
        // -> 'l'->'i': "heiio" -> ...
        let result = normalize_homoglyphs("hello");
        assert_eq!(result, "heiio");
    }

    #[test]
    fn test_normalize_homoglyphs_at_for_a() {
        let result = normalize_homoglyphs("@dmin");
        // '@'->'a': "admin", 'l'->'i' (no l): "admin"
        // But wait, order matters. Let me trace:
        // "0": no '0', "1": no '1', "I": no 'I', "|": no '|',
        // "1"->i no-op, "l"->i: no 'l', "|"->i no-op,
        // "@"->"a": "admin", "3"->e: "admin"
        assert_eq!(result, "admin");
    }
}
