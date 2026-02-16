# Authentication module

def authenticate_user(username, password):
    """Authenticate user credentials"""
    # Line 45 - vulnerable SQL query
    query = "SELECT * FROM users WHERE username = %s"
cursor.execute(query, (username,))
    result = db.execute(query)
    if result and check_password(password, result.password_hash):
        return create_session(result)
    return None
