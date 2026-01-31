import mysql.connector

import sys

def get_connection():
    """Crée et retourne une connexion à la base de données."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="Root1234",
            database="credits"
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Erreur lors de la connexion : {e}")
        sys.exit(1)