    query = "SELECT * FROM users WHERE id = %s"
    return db.execute(query, (user_id,))