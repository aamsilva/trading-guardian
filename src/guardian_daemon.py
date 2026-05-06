#!/usr/bin/env python3
"""
Trading Guardian Daemon - Continuous Operation (5min cycles)
Tier-1 Trading Grade: Real execution, Health monitoring, Multi-strategy
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-10s | %(levelname)-7s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'guardian_daemon.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('GuardianDaemon')

# Graceful shutdown
import signal
running = True

def signal_handler(sig, frame):
    global running
    logger.info("🛑 Received shutdown signal, finishing current cycle...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main daemon loop"""
    from guardian_core import TradingGuardian
    
    logger.info("=" * 60)
    logger.info("🚀 Trading Guardian Daemon starting...")
    logger.info("=" * 60)
    
    # Initialize Guardian
    try:
        guardian = TradingGuardian()
        logger.info(f"✅ Guardian initialized | Credentials: {guardian.credentials_ok}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Guardian: {e}")
        return
    
    # Initialize Alpaca Executors (Paper + Live dual mode)
    try:
        _ = guardian.alpaca_executor_paper
        account_paper = guardian.alpaca_executor_paper.get_account()
        if account_paper:
            logger.info(f"💰 Paper Account: ${float(account_paper.get('cash', 0)):.2f}")
            logger.info(f"📊 Paper Buying Power: ${float(account_paper.get('buying_power', 0)):.2f}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Alpaca Paper: {e}")
        return
    
    # Try Live account (optional - may not have credentials)
    try:
        live_exec = guardian.alpaca_executor_live
        if live_exec:
            account_live = live_exec.get_account()
            if account_live:
                logger.info(f"💰 LIVE Account: ${float(account_live.get('cash', 0)):.2f}")
                logger.info(f"📊 LIVE Buying Power: ${float(account_live.get('buying_power', 0)):.2f}")
    except Exception as e:
        logger.warning(f"⚠️  Live account unavailable: {e}")
    
    cycle_count = 0
    check_interval = 300  # 5 minutes
    
    while running:
        cycle_count += 1
        cycle_start = time.time()
        
        logger.info("-" * 60)
        logger.info(f"🔄 CYCLE #{cycle_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 60)
        
        # State accumulator for this cycle
        cycle_state = {
            "timestamp": datetime.now().isoformat(),
            "cycle": cycle_count,
            "paper": {"account": {}, "positions": []},
            "live": {"account": {}, "positions": []},
            "trades": {"executed": 0, "failed": 0, "recent": []},
            "health": {},
            "strategies": {"testing": [], "approved": [], "validated": 0, "total": 0},
            "execution": {"orders": 0, "filled": 0, "latency_ms": 0.0},
            "risk": {"leverage": 0.0, "exposure": 0.0},
            "uptime_pct": 100.0,
            "checks": cycle_count
        }
        
        try:
            # ========== PHASE 1: HEALTH CHECK ==========
            logger.info("🏥 Running health checks...")
            health = guardian.get_health()
            cycle_state["health"] = health
            logger.info(f"   Health Score: {health['overall_score']:.1f} | Status: {health['status']}")
            
            if health['overall_score'] < 50:
                logger.error("❌ Health score too low, skipping this cycle")
                time.sleep(check_interval)
                continue
            
            # ========== PHASE 2: AGGREGATE SIGNALS ==========
            logger.info("📡 Aggregating signals from all strategies...")
            signals = guardian.aggregate_signals()
            
            # Capture Paper account state
            try:
                account_paper = guardian.alpaca_executor_paper.get_account()
                positions_paper = guardian.alpaca_executor_paper.get_positions()
                cycle_state["paper"]["account"] = {
                    "cash": float(account_paper.get("cash", 0)),
                    "buying_power": float(account_paper.get("buying_power", 0)),
                    "portfolio_value": float(account_paper.get("portfolio_value", 0))
                }
                if positions_paper:
                    for sym, data in positions_paper.items():
                        cycle_state["paper"]["positions"].append({
                            "symbol": sym,
                            "qty": data.get("qty", 0),
                            "current": data.get("current", 0),
                            "pnl": data.get("pnl", 0),
                            "market_value": data.get("market_value", 0)
                        })
            except Exception as e:
                logger.warning(f"   ⚠️  Paper state capture failed: {e}")
            
            # Capture Live account state
            try:
                live_exec = guardian.alpaca_executor_live
                if live_exec:
                    account_live = live_exec.get_account()
                    positions_live = live_exec.get_positions()
                    cycle_state["live"]["account"] = {
                        "cash": float(account_live.get("cash", 0)),
                        "buying_power": float(account_live.get("buying_power", 0)),
                        "portfolio_value": float(account_live.get("portfolio_value", 0))
                    }
                    if positions_live:
                        for sym, data in positions_live.items():
                            cycle_state["live"]["positions"].append({
                                "symbol": sym,
                                "qty": data.get("qty", 0),
                                "current": data.get("current", 0),
                                "pnl": data.get("pnl", 0),
                                "market_value": data.get("market_value", 0)
                            })
            except Exception as e:
                logger.warning(f"   ⚠️  Live state capture failed: {e}")
            
            if not signals:
                logger.info("   No buy signals generated this cycle")
            else:
                logger.info(f"   ✅ Generated {len(signals)} buy signals")
                
                # ========== PHASE 3: EXECUTE TRADES ==========
                executed = 0
                failed = 0
                
                for signal in signals:
                    symbol = signal['symbol']
                    qty = signal['qty']
                    
                    logger.info(f"   📈 Processing {symbol} (qty={qty:.4f})...")
                    
                    success, msg, details = guardian.execute_real_trade(signal)
                    
                    if success:
                        executed += 1
                        mode = details.get('mode', 'PAPER')
                        logger.info(f"      ✅ Trade executed: {msg} [{mode}]")
                        cycle_state["trades"]["recent"].append({
                            "symbol": symbol,
                            "qty": qty,
                            "mode": mode,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        failed += 1
                        logger.error(f"      ❌ Trade failed: {msg}")
                
                cycle_state["trades"]["executed"] = executed
                cycle_state["trades"]["failed"] = failed
                logger.info(f"   📊 Results: {executed} executed, {failed} failed")
            
            # ========== PHASE 4: STRATEGY BACKTEST DATA ==========
            try:
                import json
                from pathlib import Path
                exp_file = Path(__file__).parent.parent / "data" / "experiments.jsonl"
                if exp_file.exists():
                    strategies_testing = []
                    strategies_approved = []
                    validated = 0
                    total = 0
                    with open(exp_file, "r") as f:
                        for line in f:
                            try:
                                exp = json.loads(line.strip())
                                total += 1
                                name = exp.get("strategy_name", exp.get("strategy", "Unknown"))
                                sharpe = exp.get("sharpe_ratio", 0)
                                win_rate = exp.get("win_rate", 0)
                                dd = exp.get("max_drawdown_pct", exp.get("max_drawdown", 100))
                                strategy_info = f"{name}: {win_rate*100:.1f}%, Sharpe {sharpe:.2f}"
                                if sharpe > 2.0 and dd < 5.0:
                                    validated += 1
                                    strategies_approved.append(strategy_info)
                                else:
                                    strategies_testing.append(strategy_info)
                            except json.JSONDecodeError:
                                continue
                    cycle_state["strategies"]["testing"] = strategies_testing[:3]
                    cycle_state["strategies"]["approved"] = strategies_approved[:2]
                    cycle_state["strategies"]["validated"] = validated
                    cycle_state["strategies"]["total"] = total
            except Exception as e:
                logger.warning(f"   ⚠️  Strategy data capture failed: {e}")
            
            # ========== PHASE 5: AUTORESEARCH + PLATFORM DISCOVERY ==========
            if cycle_count % 12 == 0:  # Every 12 cycles = 1 hour
                logger.info("🔬 Running AutoResearch cycle...")
                try:
                    result = guardian.run_autoresearch_cycle()
                    logger.info(f"   AutoResearch: {result}")
                except Exception as e:
                    logger.error(f"   ❌ AutoResearch failed: {e}")
            
            # Platform Discovery every 60 cycles (5 hours)
            if cycle_count % 60 == 0:
                logger.info("🚀 Running Platform Discovery cycle...")
                try:
                    from platform_discovery import PlatformDiscovery
                    discovery = PlatformDiscovery()
                    result = discovery.run_discovery_cycle()
                    logger.info(f"   Platform Discovery: {result}")
                except Exception as e:
                    logger.error(f"   ❌ Platform Discovery failed: {e}")
            
            # ========== CYCLE SUMMARY ==========
            cycle_time = time.time() - cycle_start
            logger.info(f"✅ Cycle #{cycle_count} completed in {cycle_time:.1f}s")
            logger.info(f"   Total Trades: {guardian.metrics.total_trades}")
            logger.info(f"   Success Rate: {guardian.metrics.success_rate():.1f}%")
            
            # Update execution stats
            cycle_state["execution"]["orders"] = guardian.metrics.total_trades
            cycle_state["execution"]["filled"] = guardian.metrics.successful_trades
            cycle_state["execution"]["latency_ms"] = 0  # TODO: implement latency tracking
            
            # Update risk metrics
            total_exposure = sum(p.get("market_value", 0) for p in cycle_state["paper"]["positions"])
            total_exposure += sum(p.get("market_value", 0) for p in cycle_state["live"]["positions"])
            total_balance = cycle_state["paper"]["account"].get("cash", 0) + cycle_state["live"]["account"].get("cash", 0)
            cycle_state["risk"]["exposure"] = total_exposure
            cycle_state["risk"]["leverage"] = total_exposure / total_balance if total_balance > 0 else 0.0
            
            # Write state to file for report script (NO Alpaca calls in report!)
            try:
                state_file = Path(__file__).parent.parent / "data" / "guardian_state.json"
                state_file.parent.mkdir(exist_ok=True)
                with open(state_file, "w") as f:
                    json.dump(cycle_state, f, indent=2, default=str)
                logger.info(f"   💾 State saved to {state_file}")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to save state: {e}")
            
        except Exception as e:
            logger.error(f"❌ Cycle #{cycle_count} error: {e}")
            guardian.metrics.api_errors += 1
        
        # ========== WAIT FOR NEXT CYCLE ==========
        if running:
            logger.info(f"😴 Sleeping {check_interval}s until next cycle...")
            # Sleep in small increments to allow graceful shutdown
            for _ in range(check_interval):
                if not running:
                    break
                time.sleep(1)
    
    logger.info("=" * 60)
    logger.info("🛑 Trading Guardian Daemon stopped")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
