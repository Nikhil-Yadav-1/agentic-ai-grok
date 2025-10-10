import sqlite3
import os

# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chatbot.db")

# Connect to the database (creates it if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create the conversations table
cursor.execute('''
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"Database created successfully at {db_path}")
print("Table 'conversations' created successfully!")
