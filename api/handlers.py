# Remediation Plan: [Tampering] Missing input validation

**Severity:** high
**Category:** threat-model
**Estimated Effort:** 8-12 hours

## Summary
Implement comprehensive input validation in API handlers to prevent tampering attacks by sanitizing and validating all user inputs before processing

## Affected Components
- api/handlers.py
- input validation middleware
- request processing pipeline

## Implementation Steps
### Step 1: Audit existing input points
Review all functions in handlers.py that accept user input including query parameters, request body, headers, and URL path parameters. Document all input sources and their expected data types.

**Files to modify:**
- `api/handlers.py`

**Example code:**
```python
# Document input points like:
# POST /api/user - expects: {name: str, email: str, age: int}
# GET /api/user/{user_id} - expects: user_id as integer
# Headers: Authorization, Content-Type
```

_Note: Create a comprehensive inventory of all input vectors_

### Step 2: Create input validation schemas
Define validation schemas for each endpoint using a validation library like Pydantic or Marshmallow. Include data types, length limits, format constraints, and allowed values.

**Files to modify:**
- `api/schemas.py`
- `api/handlers.py`

**Example code:**
```python
from pydantic import BaseModel, validator, EmailStr
from typing import Optional

class UserCreateSchema(BaseModel):
    name: str
    email: EmailStr
    age: int
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 100:
            raise ValueError('Name too long')
        return v.strip()
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Invalid age')
        return v
```

_Note: Use strong typing and comprehensive validation rules_

### Step 3: Implement input sanitization
Add input sanitization functions to clean and normalize input data. Remove or escape potentially dangerous characters, normalize whitespace, and convert to appropriate data types.

**Files to modify:**
- `api/utils.py`
- `api/handlers.py`

**Example code:**
```python
import html
import re
from typing import Any

def sanitize_string(input_str: str, max_length: int = 255) -> str:
    """Sanitize string input to prevent injection attacks"""
    if not isinstance(input_str, str):
        raise ValueError("Input must be a string")
    
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', input_str)
    
    # HTML escape
    sanitized = html.escape(sanitized)
    
    # Trim and limit length
    sanitized = sanitized.strip()[:max_length]
    
    return sanitized

def validate_integer(value: Any, min_val: int = None, max_val: int = None) -> int:
    """Validate and convert integer input"""
    try:
        int_val = int(value)
        if min_val is not None and int_val < min_val:
            raise ValueError(f"Value must be >= {min_val}")
        if max_val is not None and int_val > max_val:
            raise ValueError(f"Value must be <= {max_val}")
        return int_val
    except (ValueError, TypeError):
        raise ValueError("Invalid integer value")
```

_Note: Focus on common injection attack vectors_

### Step 4: Update handler functions with validation
Modify each handler function to validate inputs using the defined schemas and sanitization functions. Add proper error handling for validation failures.

**Files to modify:**
- `api/handlers.py`

**Example code:**
```python
from flask import request, jsonify
from pydantic import ValidationError
from .schemas import UserCreateSchema
from .utils import sanitize_string, validate_integer

def create_user():
    try:
        # Validate JSON payload
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        # Validate against schema
        user_data = UserCreateSchema(**request.json)
        
        # Additional sanitization if needed
        user_data.name = sanitize_string(user_data.name, 100)
        
        # Process validated data
        result = process_user_creation(user_data)
        return jsonify(result), 201
        
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

def get_user(user_id):
    try:
        # Validate path parameter
        validated_id = validate_integer(user_id, min_val=1)
        
        # Process with validated input
        user = get_user_by_id(validated_id)
        return jsonify(user), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
```

_Note: Ensure all user inputs are validated before processing_

### Step 5: Add request size and rate limiting
Implement request size limits and basic rate limiting to prevent abuse and resource exhaustion attacks.

**Files to modify:**
- `api/middleware.py`
- `api/handlers.py`

**Example code:**
```python
from flask import request, jsonify
from functools import wraps
import time

# Request size validation
def validate_request_size(max_size=1024*1024):  # 1MB default
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.content_length and request.content_length > max_size:
                return jsonify({"error": "Request too large"}), 413
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Apply to handlers
@validate_request_size(max_size=10240)  # 10KB limit
def create_user():
    # ... existing code
```

_Note: Protect against DoS attacks through resource limits_

### Step 6: Implement comprehensive error handling
Add proper error handling that doesn't leak sensitive information while providing useful feedback for legitimate users.

**Files to modify:**
- `api/handlers.py`
- `api/error_handlers.py`

**Example code:**
```python
import logging
from flask import jsonify

# Configure secure logging
logger = logging.getLogger(__name__)

def handle_validation_error(error):
    """Handle validation errors securely"""
    # Log detailed error for debugging
    logger.warning(f"Validation error: {str(error)}")
    
    # Return generic error to user
    return jsonify({
        "error": "Invalid input provided",
        "message": "Please check your input and try again"
    }), 400

def handle_server_error(error):
    """Handle server errors without leaking information"""
    # Log detailed error for debugging
    logger.error(f"Server error: {str(error)}")
    
    # Return generic error to user
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again later"
    }), 500
```

_Note: Balance security with usability in error messages_

## Security Considerations
- Validate all input at the application boundary before any processing
- Use whitelist validation (allow known good) rather than blacklist (block known bad)
- Sanitize input to prevent injection attacks including SQL injection, XSS, and command injection
- Implement proper error handling that doesn't leak sensitive system information
- Log validation failures for security monitoring and incident response
- Apply defense in depth with multiple validation layers
- Regularly update validation rules based on new threat intelligence

## Best Practices
- Use established validation libraries rather than custom regex patterns
- Validate data types, lengths, formats, and business logic constraints
- Perform validation as early as possible in the request lifecycle
- Use parameterized queries or ORM methods to prevent SQL injection
- Implement request size limits to prevent resource exhaustion
- Log security events for monitoring and alerting
- Regularly review and update validation rules
- Use content-type validation for API endpoints

## Acceptance Criteria
- [ ] All API endpoints validate input according to defined schemas
- [ ] Invalid input is rejected with appropriate HTTP status codes (400 Bad Request)
- [ ] Input validation prevents common injection attacks (SQL, XSS, command injection)
- [ ] Request size limits are enforced to prevent DoS attacks
- [ ] Error messages do not leak sensitive system information
- [ ] All validation failures are logged for security monitoring
- [ ] Unit tests cover both valid and invalid input scenarios
- [ ] Security testing confirms tampering attempts are blocked
- [ ] Performance impact of validation is within acceptable limits
