# Remediation Plan: 

**Severity:** medium
**Category:** threat-model
**Estimated Effort:** 6-8 hours

## Summary
Implement comprehensive threat modeling for prompt injection guard patterns to identify security gaps and enhance protection mechanisms

## Affected Components
- prompt-injection-guard-wasm
- pattern recognition system
- security validation layer

## Implementation Steps
### Step 1: Document current threat model for prompt injection patterns
Create formal threat model documentation identifying assets, threats, and attack vectors specific to prompt injection patterns

**Files to modify:**
- `guards/rust-guards/prompt-injection-guard-wasm/THREAT_MODEL.md`

**Example code:**
```python
# Threat Model for Prompt Injection Guard

## Assets
- Pattern matching algorithms
- User input validation
- LLM prompt processing

## Threats
- Malicious prompt crafting
- Pattern bypass attempts
- Input encoding attacks

## Attack Vectors
- Direct injection
- Indirect injection
- Context manipulation
```

_Note: Use STRIDE methodology to systematically identify threats_

### Step 2: Add security validation to pattern matching functions
Implement input sanitization and validation before pattern matching to prevent malicious pattern exploitation

**Files to modify:**
- `guards/rust-guards/prompt-injection-guard-wasm/src/patterns.rs`

**Example code:**
```python
use regex::Regex;
use std::collections::HashSet;

pub struct SecurePatternMatcher {
    max_input_length: usize,
    blocked_chars: HashSet<char>,
    sanitization_regex: Regex,
}

impl SecurePatternMatcher {
    pub fn new() -> Self {
        Self {
            max_input_length: 10000,
            blocked_chars: ['<', '>', '&', '"', '\''].iter().cloned().collect(),
            sanitization_regex: Regex::new(r"[\x00-\x1F\x7F-\x9F]").unwrap(),
        }
    }
    
    pub fn validate_input(&self, input: &str) -> Result<String, SecurityError> {
        if input.len() > self.max_input_length {
            return Err(SecurityError::InputTooLong);
        }
        
        let sanitized = self.sanitization_regex.replace_all(input, "");
        Ok(sanitized.to_string())
    }
}
```

_Note: Focus on preventing pattern injection and ensuring safe input processing_

### Step 3: Implement secure pattern compilation
Add validation for pattern definitions to prevent malicious regex patterns that could cause DoS or bypass security

**Files to modify:**
- `guards/rust-guards/prompt-injection-guard-wasm/src/patterns.rs`

**Example code:**
```python
pub fn compile_secure_pattern(pattern: &str) -> Result<Regex, PatternError> {
    // Validate pattern complexity to prevent ReDoS
    if pattern.len() > MAX_PATTERN_LENGTH {
        return Err(PatternError::PatternTooComplex);
    }
    
    // Check for dangerous constructs
    let dangerous_patterns = [
        r"(.*)+",  // Catastrophic backtracking
        r"(a+)+",  // Nested quantifiers
        r"(a|a)*" // Alternation with overlap
    ];
    
    for dangerous in &dangerous_patterns {
        if pattern.contains(dangerous) {
            return Err(PatternError::UnsafePattern);
        }
    }
    
    Regex::new(pattern).map_err(|e| PatternError::CompilationError(e))
}
```

_Note: Prevent ReDoS attacks and ensure pattern safety_

### Step 4: Add comprehensive security testing
Create security-focused test cases that validate threat model assumptions and test attack scenarios

**Files to modify:**
- `guards/rust-guards/prompt-injection-guard-wasm/src/patterns.rs`
- `guards/rust-guards/prompt-injection-guard-wasm/tests/security_tests.rs`

**Example code:**
```python
#[cfg(test)]
mod security_tests {
    use super::*;
    
    #[test]
    fn test_malicious_pattern_rejection() {
        let malicious_patterns = [
            "(a+)+$",  // ReDoS pattern
            ".*.*.*.*.*.*foo",  // Catastrophic backtracking
        ];
        
        for pattern in &malicious_patterns {
            assert!(compile_secure_pattern(pattern).is_err());
        }
    }
    
    #[test]
    fn test_input_sanitization() {
        let matcher = SecurePatternMatcher::new();
        let malicious_inputs = [
            "\x00malicious\x1F",
            "<script>alert('xss')</script>",
            "\u{200B}hidden\u{200C}chars",
        ];
        
        for input in &malicious_inputs {
            let result = matcher.validate_input(input);
            assert!(result.is_ok());
            assert!(!result.unwrap().contains('\x00'));
        }
    }
}
```

_Note: Cover edge cases and known attack vectors_

### Step 5: Implement security monitoring and logging
Add security event logging to detect and monitor potential attacks or pattern bypass attempts

**Files to modify:**
- `guards/rust-guards/prompt-injection-guard-wasm/src/patterns.rs`

**Example code:**
```python
use log::{warn, info, error};

pub struct SecurityLogger;

impl SecurityLogger {
    pub fn log_suspicious_input(&self, input: &str, reason: &str) {
        warn!("Suspicious input detected: reason={}, input_hash={:x}", 
              reason, self.hash_input(input));
    }
    
    pub fn log_pattern_match(&self, pattern_id: &str, confidence: f32) {
        info!("Pattern matched: id={}, confidence={}", pattern_id, confidence);
    }
    
    pub fn log_security_error(&self, error: &SecurityError) {
        error!("Security validation failed: {:?}", error);
    }
    
    fn hash_input(&self, input: &str) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        input.hash(&mut hasher);
        hasher.finish()
    }
}
```

_Note: Avoid logging sensitive data directly, use hashes for input tracking_

## Security Considerations
- Prevent Regular Expression Denial of Service (ReDoS) attacks through pattern complexity validation
- Implement input sanitization to prevent injection attacks through pattern inputs
- Add rate limiting to prevent automated pattern bypass attempts
- Ensure logging doesn't expose sensitive information while maintaining security visibility
- Validate all external inputs before processing to maintain security boundaries

## Best Practices
- Use defense in depth by implementing multiple validation layers
- Follow principle of least privilege in pattern matching permissions
- Implement fail-secure defaults where uncertain inputs are blocked
- Regular security testing with automated fuzzing of pattern inputs
- Keep security patterns updated based on emerging threat intelligence
- Use constant-time operations where possible to prevent timing attacks

## Acceptance Criteria
- [ ] All pattern compilation includes security validation that rejects unsafe patterns
- [ ] Input sanitization successfully prevents injection of malicious content
- [ ] Security test suite covers all identified threat vectors from threat model
- [ ] Logging captures security events without exposing sensitive data
- [ ] Performance impact of security measures is within acceptable limits (< 10% overhead)
- [ ] Threat model documentation is complete and regularly maintained
