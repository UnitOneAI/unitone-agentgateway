/// Calculate Levenshtein similarity ratio between two strings.
/// Returns a value between 0.0 (completely different) and 1.0 (identical).
///
/// Direct port of the Python `levenshtein_ratio` function.
pub fn levenshtein_ratio(s1: &str, s2: &str) -> f64 {
    if s1.is_empty() || s2.is_empty() {
        return 0.0;
    }
    if s1 == s2 {
        return 1.0;
    }

    let chars1: Vec<char> = s1.chars().collect();
    let chars2: Vec<char> = s2.chars().collect();

    // Ensure chars1 is the longer string (matching Python's swap)
    let (chars1, chars2) = if chars1.len() < chars2.len() {
        (chars2, chars1)
    } else {
        (chars1, chars2)
    };

    let len1 = chars1.len();
    let len2 = chars2.len();

    let mut distances: Vec<usize> = (0..=len2).collect();

    for (i1, c1) in chars1.iter().enumerate() {
        let mut new_distances = vec![i1 + 1];
        for (i2, c2) in chars2.iter().enumerate() {
            let cost = if c1 == c2 {
                distances[i2]
            } else {
                1 + distances[i2]
                    .min(distances[i2 + 1])
                    .min(*new_distances.last().unwrap())
            };
            new_distances.push(cost);
        }
        distances = new_distances;
    }

    let distance = *distances.last().unwrap();
    1.0 - (distance as f64 / len1.max(len2) as f64)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identical_strings() {
        assert!((levenshtein_ratio("hello", "hello") - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_empty_strings() {
        assert!((levenshtein_ratio("", "hello") - 0.0).abs() < f64::EPSILON);
        assert!((levenshtein_ratio("hello", "") - 0.0).abs() < f64::EPSILON);
        assert!((levenshtein_ratio("", "") - 0.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_completely_different() {
        let ratio = levenshtein_ratio("abc", "xyz");
        assert!(ratio < 0.5);
    }

    #[test]
    fn test_single_char_difference() {
        let ratio = levenshtein_ratio("finance-tools", "finance-toals");
        assert!(ratio > 0.85, "Expected > 0.85, got {}", ratio);
    }

    #[test]
    fn test_finance_tools_vs_totally_different() {
        let ratio = levenshtein_ratio("finance-tools", "totally-different");
        assert!(ratio < 0.85, "Expected < 0.85, got {}", ratio);
    }

    #[test]
    fn test_symmetric() {
        let r1 = levenshtein_ratio("abc", "abd");
        let r2 = levenshtein_ratio("abd", "abc");
        assert!((r1 - r2).abs() < f64::EPSILON);
    }
}
