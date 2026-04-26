    query = "SELECT * FROM users WHERE username = ?"
    result = db.execute(query, (username,))