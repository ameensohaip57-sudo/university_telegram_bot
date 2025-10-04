import sqlite3
from datetime import datetime

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    return sqlite3.connect('database/university_bot.db')

def init_database():
    """تهيئة قاعدة البيانات والجداول"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # نفس كود إنشاء الجداول من bot.py
    # ... (انسخ كود init_db هنا)
    
    conn.commit()
    conn.close()