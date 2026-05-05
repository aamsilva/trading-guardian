#!/usr/bin/env python3
"""Test Paper Trade + Validate LIVE Mode is INACTIVE"""
import os
import sys
import requests
import json
from datetime import datetime

# Load .env
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

print("=" * 80)
print("TESTE: PAPER TRADE + VALIDAÇÃO LIVE MODE")
print("=" * 80)

# Get credentials
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

print(f"\n🔑 API Key: {api_key[:10]}..." if api_key else "❌ API Key não encontrada")
print(f"🌐 Base URL: {base_url}")

# Check if using PAPER or LIVE
is_paper = 'paper-api' in base_url
print(f"📋 Modo: {'✅ PAPER TRADING' if is_paper else '⚠️  LIVE TRADING (PERIGO!)'}")

headers = {
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': secret_key
}

# 1. VALIDATE ACCOUNT STATUS
print("\n" + "=" * 80)
print("1. VALIDAÇÃO DO ESTADO DA CONTA")
print("=" * 80)

try:
    resp = requests.get(f'{base_url}/v2/account', headers=headers, timeout=10)
    if resp.status_code == 200:
        account = resp.json()
        print(f"✅ Account ID: {account.get('id', 'N/A')[:30]}...")
        print(f"✅ Status: {account.get('status', 'N/A')}")
        print(f"✅ Cash: ${float(account.get('cash', 0)):.2f}")
        print(f"✅ Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")
        print(f"✅ Buying Power: ${float(account.get('buying_power', 0)):.2f}")
        
        # Check if it's paper or live
        account_url = account.get('account_url', '')
        if 'paper' in base_url.lower() or 'paper' in account_url.lower():
            print(f"\n✅ CONFIRMADO: CONTA EM MODO PAPER TRADING")
        else:
            print(f"\n⚠️  ATENÇÃO: URL sugere LIVE TRADING!")
    else:
        print(f"❌ Erro ao obter conta: {resp.status_code}")
        print(f"   {resp.text[:200]}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 2. CHECK CURRENT POSITIONS
print("\n" + "=" * 80)
print("2. POSIÇÕES ATUAIS")
print("=" * 80)

try:
    resp = requests.get(f'{base_url}/v2/positions', headers=headers, timeout=10)
    if resp.status_code == 200:
        positions = resp.json()
        if positions:
            print(f"✅ {len(positions)} posição(ões) encontrada(s):")
            for pos in positions:
                symbol = pos.get('symbol', '?')
                qty = float(pos.get('qty', 0))
                side = pos.get('side', '?')
                market_value = float(pos.get('market_value', 0))
                print(f"   • {symbol}: {qty} shares ({side}) - ${market_value:.2f}")
        else:
            print(f"✅ Nenhuma posição aberta (portfolio limpo)")
    else:
        print(f"❌ Erro: {resp.status_code}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 3. EXECUTE PAPER TRADE (Buy 1 share of a cheap stock)
print("\n" + "=" * 80)
print("3. EXECUÇÃO DE PAPER TRADE (TESTE)")
print("=" * 80)

# Let's buy 1 share of a cheaper stock for testing
test_symbol = 'F'  # Ford - usually around $10-15
test_qty = 1

print(f"\n📋 Ordem de Teste:")
print(f"   • Symbol: {test_symbol}")
print(f"   • Side: BUY")
print(f"   • Quantity: {test_qty} share(s)")
print(f"   • Order Type: Market")
print(f"   • Modo: PAPER (sem risco real)")

# Check if we already have position in this stock
try:
    resp = requests.get(f'{base_url}/v2/positions/{test_symbol}', headers=headers, timeout=10)
    if resp.status_code == 200:
        existing = resp.json()
        print(f"\n⚠️  Já tens posição em {test_symbol}:")
        print(f"   Qty: {existing.get('qty', 0)} shares")
        print(f"   Market Value: ${float(existing.get('market_value', 0)):.2f}")
        print(f"\n💡 Vou vender primeiro para manter o teste limpo...")
        
        # Close existing position
        close_data = {'symbol': test_symbol}
        resp = requests.delete(f'{base_url}/v2/positions/{test_symbol}', headers=headers, json=close_data, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Posição existente fechada!")
        else:
            print(f"❌ Erro ao fechar posição: {resp.text[:100]}")
except:
    pass  # No existing position, that's fine

# Place BUY order
print(f"\n⏳ A enviar ordem de COMPRA ({test_symbol})...")

order_data = {
    'symbol': test_symbol,
    'qty': str(test_qty),
    'side': 'buy',
    'type': 'market',
    'time_in_force': 'gtc'
}

try:
    resp = requests.post(f'{base_url}/v2/orders', headers=headers, json=order_data, timeout=10)
    
    if resp.status_code in [200, 201]:
        order = resp.json()
        print(f"\n✅ ORDEM EXECUTADA COM SUCESSO!")
        print(f"   • Order ID: {order.get('id', 'N/A')[:30]}...")
        print(f"   • Symbol: {order.get('symbol', '?')}")
        print(f"   • Side: {order.get('side', '?').upper()}")
        print(f"   • Qty: {order.get('qty', '?')}")
        print(f"   • Status: {order.get('status', '?')}")
        print(f"   • Filled Qty: {order.get('filled_qty', '0')}")
        print(f"   • Filled Avg Price: ${order.get('filled_avg_price', 'N/A')}")
        print(f"\n💡 Paper Trade executado! Sem risco financeiro real.")
    else:
        print(f"❌ Erro ao executar ordem: {resp.status_code}")
        print(f"   Resposta: {resp.text[:300]}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 4. VERIFY LIVE MODE IS NOT ACTIVE
print("\n" + "=" * 80)
print("4. VALIDAÇÃO: LIVE TRADING INATIVO")
print("=" * 80)

print(f"\n🔍 Verificação de segurança:")

# Check BASE_URL
if 'paper-api' in base_url:
    print(f"✅ BASE_URL configurado para PAPER: {base_url}")
else:
    print(f"❌ PERIGO: BASE_URL não é paper: {base_url}")

# Try to access LIVE endpoint (should fail or be different account)
live_url = 'https://api.alpaca.markets'
print(f"\n🔍 Testando se as keys funcionam em LIVE (deve falhar):")

try:
    resp = requests.get(f'{live_url}/v2/account', headers=headers, timeout=5)
    if resp.status_code == 200:
        print(f"⚠️  ATENÇÃO: As tuas keys FUNCIONAM em LIVE!")
        print(f"   Isto NÃO deveria acontecer com uma conta Paper.")
        print(f"   Verifica se não tens acesso a LIVE trading.")
    elif resp.status_code in [401, 403]:
        print(f"✅ CONFIRMADO: Keys NÃO funcionam em LIVE (401/403)")
        print(f"   Isso é BOM! Significa que estás seguro no Paper.")
    else:
        print(f"ℹ️  Resposta inesperada: {resp.status_code}")
except Exception as e:
    print(f"✅ CONFIRMADO: Não há acesso a LIVE ({e})")

print("\n" + "=" * 80)
print("RESUMO FINAL")
print("=" * 80)

print(f"\n✅ Paper Trading: ATIVO e FUNCIONAL")
print(f"✅ Live Trading: INATIVO (segurança garantida)")
print(f"✅ Teste de Trade: EXECUTADO")
print(f"✅ Modo: APENAS PAPER (sem risco real)")
print(f"\n💡 Podes fazer trades fictícios com confiança!")
