import os
from dotenv import load_dotenv
from sqlalchemy.engine.url import URL

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta'

    # Usamos .strip() para limpiar espacios en blanco accidentales
    DB_USER = os.environ.get('DB_USER', '').strip()
    DB_PASS = os.environ.get('DB_PASS', '').strip()
    DB_HOST = os.environ.get('DB_HOST', '').strip()
    DB_NAME = os.environ.get('DB_NAME', '').strip()
    DB_PORT = os.environ.get('DB_PORT', '5432').strip()

    if DB_USER and DB_PASS and DB_HOST and DB_NAME:
        SQLALCHEMY_DATABASE_URI = URL.create(
            drivername="postgresql+pg8000",
            username=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME
        )
        # Imprimimos el nombre entre corchetes para ver si hay espacios ocultos
        print(f"Conectando a BD: [{DB_NAME}] en [{DB_HOST}] usando pg8000")
    else:
        print("ADVERTENCIA: Faltan datos. Usando SQLite.")
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }