from db import get_connection


def validation(numero):
    conn = get_connection()
    cur = conn.cursor()

    requete = """
        SELECT COUNT(*) 
        FROM transactions 
        WHERE numero = %s 
        AND date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
    """

    cur.execute(requete, (numero,))
    (nombre,) = cur.fetchone() # Récupère le résultat du COUNT
    conn.commit()
    cur.close()
    conn.close()
    
    return nombre > 0