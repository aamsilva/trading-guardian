#!/usr/bin/env python3
"""Check post-trade status"""
import os
import sys
import requests
import json

# Load .env
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

headers = {
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': secret_key
}

print("=" * 70)
print("VERIFICAÇÃO PÓS-TRADE")
print("=" * 70)

# Check current positions
print("\n📊 POSIÇÕES ATUAIS:")
try:
    resp = requests.get(f'{base_url}/v2/positions', headers=headers, timeout=10)
    if resp.status_code == 200:
        positions = resp.json()
        if positions:
            for pos in positions:
                symbol = pos.get('symbol', '?')
                qty = float(pos.get('qty', 0))
                market_value = float(pos.get('market_value', 0))
                current_price = float(pos.get('current_price', 0))
                print(f"   • {symbol}: {qty} shares - ${market_value:.2f} (price: ${current_price:.2f})")
        else:
            print("   Nenhuma posição aberta")
    else:
        print(f"   Erro: {resp.status_code}")
except Exception as e:
    print(f"   Erro: {e}")

# Check account balance
print("\n💰 SALDO DA CONTA:")
try:
    resp = requests.get(f'{base_url}/v2/account', headers=headers, timeout=10)
    if resp.status_code == 200:
        account = resp.json()
        print(f"   Cash: ${float(account.get('cash', 0)):.2f}")
        print(f"   Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")
        print(f"   Buying Power: ${float(account.get('buying_power', 0)):.2f}")
except Exception as e:
    print(f"   Erro: {e}")

# Check pending orders
print("\n📋 ORDENS PENDENTES:")
try:
    resp = requests.get(f'{base_url}/v2/orders?status=open', headers=headers, timeout=10)
    if resp.status_code == 200:
        orders = resp.json()
        if orders:
            for order in orders:
                print(f"   • {order.get('symbol')}: {order.get('side').upper()} {order.get('qty')} - Status: {order.get('status')}")
        else:
            print("   Nenhuma ordem pendente")
except Exception as e:
    print(f"   Erro: {e}")

# Check recent orders (last 5)
print("\n📋 ÚLTIMAS ORDENS (últimas 5):")
try:
    resp = requests.get(f'{base_url}/v2/orders?status=all&limit=5', headers=headers, timeout=10)
    if resp.status_code == 200:
        orders = resp.json()
        if orders:
            for order in orders[:5]:
                filled_qty = float(order.get('filled_qty', 0))
                avg_price = order.get('filled_avg_price')
                print(f"   • {order.get('symbol')}: {order.get('side').upper()} {order.get('qty')} - Status: {order.get('status')}")
                if filled_qty > 0:
                    print(f"     ✓ Filled: {filled_qty} @ ${float(avg_price):.2f}" if avg_price else f"     ✓ Filled: {filled_qty} shares")
        else:
            print("   Nenhuma ordem encontrada")
except Exception as e:
    print(f"   Erro: {e}")

print("\n" + "=" * 70)
print("✅ TESTE DE PAPER TRADE CONCLUÍDO!")
print("=" * 70)
print("\n💡 O trade foi executado em modo PAPER (sem risco real)")
print("   Podes verificar no dashboard da Alpaca: https://app.alpaca.markets/")
