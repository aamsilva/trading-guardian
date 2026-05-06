#!/usr/bin/env python3
"""
Trading Guardian - Ciclo Autónomo Completo
Executa: Health Check → AutoResearch → Dexter Analysis → Trading → Relatório
"""

import os
import sys
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from guardian_core import TradingGuardian, SystemStatus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("=" * 60)
    print("🛡️  TRADING GUARDIAN — CICLO AUTÓNOMO")
    print("=" * 60)
    
    # Initialize Guardian
    guardian = TradingGuardian()
    
    # Store cycle results
    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "health": None,
        "autoresearch": None,
        "dexter": None,
        "trading": None,
        "alerts": []
    }
    
    # ============================================
    # 1. HEALTH CHECK
    # ============================================
    print("\n📊 [1/5] Health Check...")
    try:
        health = guardian.get_health()
        results["health"] = health
        print(f"   Health Score: {health['overall_score']:.1f}/100")
        print(f"   Status: {health['status']}")
        
        if health['checks']:
            for check_name, check_data in health['checks'].items():
                status_icon = "✅" if check_data['status'] == "OK" else "❌"
                print(f"   {status_icon} {check_name}: {check_data['message']}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        results["alerts"].append(f"Health check failed: {e}")
    
    # ============================================
    # 2. AUTORESEARCH CYCLE (if health < 50)
    # ============================================
    health_score = results["health"]["overall_score"] if results["health"] else 0
    
    if health_score < 50:
        print("\n🧠 [2/5] AutoResearch Cycle (Health < 50)...")
        try:
            autoresearch_result = guardian.run_autoresearch_cycle()
            results["autoresearch"] = autoresearch_result
            print(f"   ✅ AutoResearch: {autoresearch_result.get('status', 'unknown')}")
        except Exception as e:
            print(f"   ❌ AutoResearch error: {e}")
            results["alerts"].append(f"AutoResearch failed: {e}")
    else:
        print(f"\n🧠 [2/5] AutoResearch Cycle (skipped - health {health_score:.1f} >= 50)")
        results["autoresearch"] = {"status": "skipped", "reason": f"health {health_score:.1f} >= 50"}
    
    # ============================================
    # 3. DEXTER ANALYSIS
    # ============================================
    print("\n🧠 [3/5] Dexter Analysis...")
    
    financial_api_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    
    if financial_api_key:
        try:
            from dexter_tools import (
                analyze_trading_opportunity,
                screen_market_opportunities,
                get_price_data
            )
            
            # Analyze a sample stock
            print("   📈 Analyzing AAPL...")
            analysis = analyze_trading_opportunity(
                "AAPL",
                "What is the current trend and should we buy?"
            )
            results["dexter"] = {
                "status": "success",
                "analysis": analysis
            }
            print(f"   ✅ AAPL analyzed")
            
            # Screen opportunities
            print("   🔍 Screening market opportunities...")
            opportunities = screen_market_opportunities({
                "market_cap": ">1000000000",
                "sector": "Technology"
            })
            results["dexter"]["opportunities"] = opportunities
            print(f"   ✅ Found {len(opportunities) if isinstance(opportunities, list) else 'N/A'} opportunities")
            
        except Exception as e:
            print(f"   ❌ Dexter Analysis error: {e}")
            results["alerts"].append(f"Dexter Analysis failed: {e}")
            results["dexter"] = {"status": "error", "message": str(e)}
    else:
        print("   ⚠️  FINANCIAL_DATASETS_API_KEY not configured")
        results["dexter"] = {"status": "skipped", "reason": "API key missing"}
        results["alerts"].append("FINANCIAL_DATASETS_API_KEY necessary for Dexter Analysis")
    
    # ============================================
    # 4. TRADING OPERATIONS
    # ============================================
    print("\n💱 [4/5] Trading Operations...")
    
    if guardian.credentials_ok:
        try:
            # Execute simulated trades
            from guardian_core import TradeOrder
            
            trades_executed = []
            
            # Trade 1: AAPL
            order1 = TradeOrder(
                symbol="AAPL",
                side="buy",
                quantity=10,
                stop_loss=95.0,
                take_profit=110.0
            )
            success1, msg1, details1 = guardian.execute_trade(order1)
            trades_executed.append({
                "symbol": "AAPL",
                "success": success1,
                "message": msg1
            })
            print(f"   {'✅' if success1 else '❌'} AAPL: {msg1}")
            
            # Trade 2: MSFT
            order2 = TradeOrder(
                symbol="MSFT",
                side="buy",
                quantity=5,
                stop_loss=280.0,
                take_profit=320.0
            )
            success2, msg2, details2 = guardian.execute_trade(order2)
            trades_executed.append({
                "symbol": "MSFT",
                "success": success2,
                "message": msg2
            })
            print(f"   {'✅' if success2 else '❌'} MSFT: {msg2}")
            
            # Trade 3: GOOGL
            order3 = TradeOrder(
                symbol="GOOGL",
                side="buy",
                quantity=3,
                stop_loss=130.0,
                take_profit=150.0
            )
            success3, msg3, details3 = guardian.execute_trade(order3)
            trades_executed.append({
                "symbol": "GOOGL",
                "success": success3,
                "message": msg3
            })
            print(f"   {'✅' if success3 else '❌'} GOOGL: {msg3}")
            
            results["trading"] = {
                "status": "completed",
                "trades": trades_executed,
                "total": len(trades_executed),
                "successful": sum(1 for t in trades_executed if t["success"])
            }
            
        except Exception as e:
            print(f"   ❌ Trading error: {e}")
            results["alerts"].append(f"Trading failed: {e}")
            results["trading"] = {"status": "error", "message": str(e)}
    else:
        print("   ⚠️  Alpaca credentials not configured - simulation only")
        results["trading"] = {"status": "skipped", "reason": "credentials missing"}
        results["alerts"].append("Alpaca credentials necessary for real trading")
    
    # ============================================
    # 5. ROLLBACK SNAPSHOTS
    # ============================================
    print("\n📸 [5/5] Snapshots...")
    try:
        snapshots = guardian.rollback.list_snapshots()
        results["snapshots"] = {
            "count": len(snapshots),
            "available": snapshots[:5]  # Show last 5
        }
        print(f"   ✅ {len(snapshots)} snapshots available")
    except Exception as e:
        print(f"   ⚠️  Snapshot check error: {e}")
        results["snapshots"] = {"count": 0, "available": []}
    
    # ============================================
    # GENERATE DISCORD REPORT
    # ============================================
    print("\n" + "=" * 60)
    print("📋 RELATÓRIO DISCORD")
    print("=" * 60)
    
    health_score = results["health"]["overall_score"] if results["health"] else 0
    health_status = results["health"]["status"] if results["health"] else "unknown"
    
    autoresearch_status = "✅"
    if results["autoresearch"]:
        if results["autoresearch"].get("status") == "skipped":
            autoresearch_status = "⏭️"
        elif results["autoresearch"].get("status") == "error":
            autoresearch_status = "❌"
    
    dexter_status = "✅" if results.get("dexter") and results["dexter"].get("status") == "success" else "❌"
    if results.get("dexter") and results["dexter"].get("status") == "skipped":
        dexter_status = "⏭️"
    
    trading_count = 0
    if results.get("trading") and results["trading"].get("status") == "completed":
        trading_count = results["trading"].get("successful", 0)
    
    snapshot_count = results.get("snapshots", {}).get("count", 0)
    
    discord_report = f"""**TRADING GUARDIAN — CICLO AUTÓNOMO** → _60min cycle complete_

📊 **Health Score**: `{health_score:.0f}/100` ({health_status})
🧠 **AutoResearch**: {autoresearch_status} {results.get("autoresearch", {}).get("status", "N/A")}
🧠 **Dexter Analysis**: {dexter_status} {"AAPL analisado" if dexter_status == "✅" else "skipped/failed"}
💱 **Trading**: {trading_count} trades executados (simulação)
📸 **Snapshots**: {snapshot_count} disponíveis (rollback ready)
⚠️ **Alertas**: {" | ".join(results["alerts"]) if results["alerts"] else "Nenhum"}

⏰ `{results["timestamp"]}` | 🔄 Próximo: `{(datetime.utcnow().replace(minute=datetime.utcnow().minute+60) if datetime.utcnow().minute+60 < 60 else datetime.utcnow().replace(hour=datetime.utcnow().hour+1, minute=0)).strftime("%Y-%m-%dT%H:%M:%SZ")}`
"""
    
    print(discord_report)
    print("=" * 60)
    
    # Save results to file for logging
    with open("/Volumes/disco1tb/projects/trading-guardian/logs/cycle_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    return discord_report

if __name__ == "__main__":
    report = main()
    # Output the report for the cron job to capture
    print("\n---DELIVERY---")
    print(report)
