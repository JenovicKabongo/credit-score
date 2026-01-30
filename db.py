import mariadb
import sys

def get_connection():
    """Crée et retourne une connexion à la base de données."""
    try:
        conn = mariadb.connect(
            host="localhost",
            port=3306,
            user="picapic",
            password="1234",
            database="credits"
        )
        return conn
    except mariadb.Error as e:
        print(f"Erreur lors de la connexion : {e}")
        sys.exit(1)