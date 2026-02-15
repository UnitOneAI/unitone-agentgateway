# Test file for security fix demonstration
def get_user_data(user_id):
    # Vulnerable: SQL injection
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)

