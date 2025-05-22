import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        conn = psycopg2.connect(
            database="dbtest",
            user="postgres",
            password="slmm",
            host="localhost",
            port="5432"
        )
        print("✅ Veritabanına başarıyla bağlanıldı!")
        return conn
    except Exception as e:
        print("❌ Veritabanı bağlantı hatası:", e)
        return None

def create_users_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS girisyap (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def create_messages_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            sender_id INTEGER REFERENCES girisyap(id),
            receiver_id INTEGER REFERENCES girisyap(id),
            message TEXT NOT NULL,
            status TEXT CHECK (status IN ('gönderildi', 'teslim edildi', 'okundu')) DEFAULT 'gönderildi',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def create_groups_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            created_by INTEGER REFERENCES girisyap(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def create_group_messages_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_messages (
            id SERIAL PRIMARY KEY,
            group_id INTEGER REFERENCES groups(id),
            sender_id INTEGER REFERENCES girisyap(id),
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_users_table()
create_messages_table()
create_groups_table()
create_group_messages_table()
