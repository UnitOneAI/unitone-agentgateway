# Test file for security fix demonstration
def get_user_data(user_id):
    # Vulnerable: SQL injection
    query = "SELECT * FROM users WHERE id = %s"
return db.execute(query, (user_id,))
    return db.execute(query)

