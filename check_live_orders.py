#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()

import requests
from datetime import datetime

api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

headers = {
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': secret_key
}

# Check positions
print('=== POSIÇÕES ATUAIS (LIVE) ===')
r = requests.get(f'{base_url}/v2/positions', headers=headers)
positions = r.json()
print(f'Status: {r.status_code}')
if r.status_code == 200:
    if len(positions) == 0:
        print('→ Nenhuma posição aberta')
    else:
        for p in positions:
            print(f"{p['symbol']}: {p['qty']} shares @ ${p['avg_entry_price']} (current: ${p['current_price']})")
else:
    print(f'Erro: {positions}')

# Check open orders
print('\n=== ORDENS ABERTAS (LIVE) ===')
r = requests.get(f'{base_url}/v2/orders?status=open&limit=50', headers=headers)
open_orders = r.json()
print(f'Status: {r.status_code}')
if r.status_code == 200:
    if len(open_orders) == 0:
        print('→ Nenhuma ordem aberta')
    else:
        for o in open_orders:
            print(f"{o['symbol']}: {o['side']} {o['qty']} - {o['status']}")
else:
    print(f'Erro: {open_orders}')

# Check today's filled orders
today = datetime.now().strftime('%Y-%m-%d')
print(f'\n=== ORDENS EXECUTADAS HOJE ({today}) ===')
r = requests.get(f'{base_url}/v2/orders?status=filled&after={today}T00:00:00Z&limit=50', headers=headers)
filled = r.json()
print(f'Status: {r.status_code}')
if r.status_code == 200:
    if len(filled) == 0:
        print('→ Nenhuma ordem executada hoje')
    else:
        for o in filled:
            print(f"✅ {o['symbol']}: {o['side']} {o['filled_qty']} @ ${o.get('filled_avg_price', 'N/A')} - {o['submitted_at']}")
else:
    print(f'Erro: {filled}')

# Account info
print(f'\n=== INFORMAÇÕES DA CONTA ===')
r = requests.get(f'{base_url}/v2/account', headers=headers)
account = r.json()
if r.status_code == 200:
    print(f"Cash: ${account['cash']}")
    print(f"Portfolio Value: ${account['portfolio_value']}")
    print(f"Buying Power: ${account['buying_power']}")
    print(f"Status: {account['status']}")
else:
    print(f'Erro: {account}')
