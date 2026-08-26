import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'consultorio-psicologico-secret-key-2026'
    
    # La variable DATABASE_URL la proporcionará Render con las credenciales de Supabase
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Fallback a SQLite local por si pruebas el código en tu computadora sin conexión
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'consultorio.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
