import pymysql
from config import DATABASE_CONFIG

def get_connection():
    return pymysql.connect(
        host=DATABASE_CONFIG["host"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
        database=DATABASE_CONFIG["database"]
    )

def store_processed_data(data):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO processed_results (timestamp, data) VALUES (NOW(), %s)", (data,))
            conn.commit()
    finally:
        conn.close()