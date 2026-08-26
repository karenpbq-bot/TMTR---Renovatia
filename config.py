import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'consultorio-psicologico-secret-key-2026'
    
    # Intenta leer la URL de Render/Supabase
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Fallback por seguridad
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'consultorio.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
