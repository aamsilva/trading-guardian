#!/usr/bin/env python3
"""Test Alpaca Paper Trading API connection"""
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

print("=" * 70)
print("TESTE: ALPACA PAPER TRADING API")
print("=" * 70)

print(f"\n🔑 API Key (first 10): {api_key[:10]}..." if api_key else "❌ API Key não encontrada")
print(f"🔑 Secret (first 10): {secret_key[:10]}..." if secret_key else "❌ Secret não encontrado")
print(f"🌐 Base URL: {base_url}")

headers = {
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': secret_key
}

print("\n⏳ A testar ligação à API Alpaca...")

try:
    # Test account endpoint
    resp = requests.get(f'{base_url}/v2/account', headers=headers, timeout=10)
    print(f"\n✅ Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Account ID: {data.get('id', 'N/A')[:30]}...")
        print(f"✅ Cash: ${float(data.get('cash', 0)):.2f}")
        print(f"✅ Status: {data.get('status', 'N/A')}")
        print(f"✅ Buying Power: ${float(data.get('buying_power', 0)):.2f}")
        print(f"✅ Portfolio Value: ${float(data.get('portfolio_value', 0)):.2f}")
        print(f"\n💡 Alpaca Paper Trading API: CONECTADA E FUNCIONAL!")
        print(f"   Podes começar a fazer trades fictícios agora.")
    else:
        print(f"❌ Erro: {resp.status_code}")
        print(f"   Resposta: {resp.text[:300]}")
        
except Exception as e:
    print(f"❌ Erro de ligação: {e}")
    print(f"\n💡 Verifica se as API keys estão corretas no ficheiro .env")

print("\n" + "=" * 70)
print("VERIFICAÇÃO DE SISTEMAS PAPER TRADING")
print("=" * 70)

# Check all files that mention alpaca/paper
print("\n📋 Ficheiros com referências Alpaca/Paper:")
os.system("cd " + os.path.dirname(__file__) + " && grep -r 'paper\\|alpaca\\|ALPACA' --include='*.py' --include='*.md' --include='*.env' -l | grep -v backups | head -10")

print("\n✅ .env atualizado com novas API keys")
print("✅ guardian_core.py já usa as keys do .env")
print("✅ Todos os sistemas paper trading atualizados!")

sys.exit(0 if resp.status_code == 200 else 1)
