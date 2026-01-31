from datetime import date, datetime
from cachetools import Cache

from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import json
import calcul
from db import get_connection
from transactions import validation

import os
from dotenv import load_dotenv

load_dotenv()  # Charge les variables du fichier .env
user_numero = os.getenv("NUMBER")


# maxsize is the size of data the Cache can hold
cache_data = Cache(maxsize=50000)


class UssdRequest(BaseModel):
    sessionID: str
    userID: str
    newSession: bool
    msisdn: str
    userData: str | None = None
    network: str


class UssdResponse(BaseModel):
    sessionID: str | None = None
    userID: str | None = None
    continueSession: bool | None = None
    msisdn: str | None = None
    message: str | None = None


class UssdState(BaseModel):
    sessionID: str
    message: str
    newSession: bool
    msisdn: str
    userData: str | None = None
    network: str
    message: str
    level: int
    part: int


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/ussd")
async def handle_ussd(ussd_request: UssdRequest):
    conn = get_connection()
    cur = conn.cursor()
    response = UssdResponse(
        sessionID=ussd_request.sessionID,
        userID=ussd_request.userID,
        msisdn=ussd_request.msisdn,
    )

    if ussd_request.newSession:
        response.message = (
            "Menu Principal"
            + "\n1. Mon Solde"
            + "\n2. Emprunter"
            + "\n3. Favoris"
            + "\n4. Reglages"
            + "\n5. Payments"
        )
        response.continueSession = True

        # Keep track of the USSD state of the user and their session

        current_state = UssdState(
            sessionID=ussd_request.sessionID,
            msisdn=ussd_request.msisdn,
            userData=ussd_request.userData,
            network=ussd_request.network,
            message=response.message,
            level=1,
            part=1,
            newSession=True,
        )

        user_response_tracker = cache_data.get(hash(ussd_request.sessionID), [])

        user_response_tracker.append(current_state)

        cache_data[hash(ussd_request.sessionID)] = user_response_tracker
    else:
        last_response = cache_data.get(hash(ussd_request.sessionID), [])[-1]

        if last_response.level == 1:
            user_data = ussd_request.userData

            if user_data == "2":
                response.message = (
                    "Entrer le montant de l'emprunt (en Franc Congolais):"
                )
                response.continueSession = True

                # Keep track of the USSD state of the user and their session

                current_state = UssdState(
                    sessionID=ussd_request.sessionID,
                    msisdn=ussd_request.msisdn,
                    userData=ussd_request.userData,
                    network=ussd_request.network,
                    message=response.message,
                    level=2,
                    part=1,
                    newSession=ussd_request.newSession,
                )

                user_response_tracker = cache_data.get(hash(ussd_request.sessionID), [])

                user_response_tracker.append(current_state)

                cache_data[hash(ussd_request.sessionID)] = user_response_tracker
            elif user_data == "1":
                if validation(user_numero):
                    try:
                        query = "SELECT montant FROM transactions WHERE numero = %s ORDER BY date DESC LIMIT 1"
                        cur.execute(query, ( user_numero,))
        
                        resultat = cur.fetchone()[0]
                        conn.commit()
                
                    finally:
                        # On ferme tout proprement
                        cur.close()
                        conn.close()
                    
                    response.message = (
                        f"Vous devez un total de {resultat} FC.")
                else:
                    response.message = (
                    "Vous n'avez pas d'emprunt en cours."
                    )
                response.continueSession = False

            elif (
                user_data == "1"
                or user_data == "3"
                or user_data == "4"
                or user_data == "5"
            ):
                response.message = "Thank you for voting!"
                response.continueSession = False
            else:
                response.message = "Bad choice!"
                response.continueSession = False
        elif last_response.level == 2:
            montant_saisi = ussd_request.userData
            if montant_saisi.isdigit():
                montant = int(montant_saisi)
                response.message = f"Vous avez demandé un emprunt de {montant} FC. \nConfirmez-vous ?\n1. Oui\n2. Non"
                response.continueSession = True
                
                # On met à jour l'état pour passer au niveau 3 (Confirmation)
                current_state = UssdState(
                    sessionID=ussd_request.sessionID,
                    msisdn=ussd_request.msisdn,
                    userData=montant_saisi, # On stocke le montant pour s'en souvenir après
                    network=ussd_request.network,
                    message=response.message,
                    level=3, 
                    part=1,
                    newSession=False,
                )
            else:
                response.message = "Montant invalide. Veuillez entrer un nombre."
                response.continueSession = True
                # On reste au niveau 2 pour qu'il réessaie
                current_state = last_response
            user_response_tracker = cache_data.get(hash(ussd_request.sessionID), [])

            user_response_tracker.append(current_state)
            cache_data[hash(ussd_request.sessionID)] = user_response_tracker

        elif last_response.level == 3:
            choix_confirmation = ussd_request.userData
            
            # Récupérer le montant stocké dans l'état précédent pour l'afficher ou l'enregistrer
            montant_final = last_response.userData

            if choix_confirmation == "1":
                # ICI : Vous feriez normalement l'appel API vers votre banque ou base de données
                decision, limite = calcul.calcul_score(user_numero, montant_final)
                if decision:
                    try:
                        cur.execute(
                        "INSERT INTO transactions (numero, montant, date) VALUES (%s, %s, %s)", 
                        (user_numero, montant_final, str(datetime.now()))
                        )
                        conn.commit()
            
                    finally:
                        # On ferme tout proprement
                        cur.close()
                        conn.close()
                    response.message = f"Succès ! L'emprunt de {montant_final} FC a été transféré sur votre compte."
                    response.continueSession = False # Termine la session USSD
                elif validation(user_numero):
                    response.message = f"Votre demande d'emprunt a été refusée. Vous avez déjà un emprunt en cours."
                    response.continueSession = False # Termine la session USSD
                else:
                    response.message = f"Vous n'êtes pas éligible à cet emprunt. Votre limite actuel est de {limite} FC."
                    response.continueSession = False # Termine la session USSD
            elif choix_confirmation == "2":
                response.message = "Opération annulée. Merci d'avoir utilisé notre service."
                response.continueSession = False
            else:
                response.message = "Choix invalide. Veuillez répondre par 1 pour Oui ou 2 pour Non."
                response.continueSession = True
                # On reste au niveau 3 en cas d'erreur de saisie
    return JSONResponse(
        content=response.model_dump(),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
