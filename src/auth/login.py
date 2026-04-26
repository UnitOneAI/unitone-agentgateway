    query = "SELECT * FROM users WHERE username = %s"
    result = db.execute(query, (username,))