import pandas
from tabulate import tabulate
from transactions import validation

def calcul_score(numero, montant):
    limite = 0
    decision = False
    montant = int(montant)

    if validation(numero):
        return decision, limite

    df = pandas.read_csv('dataset_clean2.csv')
    user_data = df[df['phone_number'] == int(numero)]
    print(user_data, flush=True)
    print(type(numero), flush=True)
    print(numero, flush=True)

    if len(user_data) == 0:
        return decision, limite
    
    user_data = user_data.iloc[0].to_dict()

    score = 0
    
    score += min((user_data['avg_txn_amount'] / 100) * 400, 400)
    
    score += min((user_data['monthly_data_usage_gb'] / 5000) * 200, 200)
    
    score += min((user_data['sim_tenure_days'] / 365.25) * 250, 250)
    
    score += min((user_data['calls_per_day'] / 300) * 150, 150)

    if 0 <= score <= 300:
        limite = 0
    elif 301 <= score <= 500:
        limite = 20000
    elif 501 <= score <= 700:
        limite = 100000
    elif 701 <= score <= 850:
        limite = 250000
    elif 851 <= score <= 1000:
        limite = 500000
    
    if montant <= limite:
        decision = True

    return decision, limite
