import mysql.connector
from flask import g

# Configuración de conexión
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'zoneclass',
    'port': 3306
}

def get_db():
    """Obtiene la conexión a la BD para la petición actual."""
    if 'db' not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db

def close_db(e=None):
    """Cierra la conexión al finalizar la petición."""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

def init_app(app):
    """Registra la función de cierre en el ciclo de vida de Flask."""
    app.teardown_appcontext(close_db)