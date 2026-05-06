#!/usr/bin/env python3
"""
Trading Guardian Daemon - Continuous Operation (5min cycles)
Tier-1 Trading Grade: Real execution, Health monitoring, Multi-strategy
"""

import os
import sys
import time
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
        
        try:
            # ========== PHASE 1: HEALTH CHECK ==========
            logger.info("🏥 Running health checks...")
            health = guardian.get_health()
            logger.info(f"   Health Score: {health['overall_score']:.1f} | Status: {health['status']}")
            
            if health['overall_score'] < 50:
                logger.error("❌ Health score too low, skipping this cycle")
                time.sleep(check_interval)
                continue
            
            # ========== PHASE 2: AGGREGATE SIGNALS ==========
            logger.info("📡 Aggregating signals from all strategies...")
            signals = guardian.aggregate_signals()
            
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
                    else:
                        failed += 1
                        logger.error(f"      ❌ Trade failed: {msg}")
                
                logger.info(f"   📊 Results: {executed} executed, {failed} failed")
            
            # ========== PHASE 4: SHOW CURRENT POSITIONS ==========
            # Paper positions
            try:
                positions_paper = guardian.alpaca_executor_paper.get_positions()
                if positions_paper:
                    logger.info(f"   📊 Paper Positions: {len(positions_paper)}")
                    for sym, data in positions_paper.items():
                        logger.info(f"      {sym}: {data['qty']} shares @ ${data['current']:.2f} (PnL: ${data['pnl']:.2f}) [PAPER]")
                else:
                    logger.info("   📊 No Paper positions")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not fetch Paper positions: {e}")
            
            # Live positions (if available)
            try:
                live_exec = guardian.alpaca_executor_live
                if live_exec:
                    positions_live = live_exec.get_positions()
                    if positions_live:
                        logger.info(f"   📊 Live Positions: {len(positions_live)}")
                        for sym, data in positions_live.items():
                            logger.info(f"      {sym}: {data['qty']} shares @ ${data['current']:.2f} (PnL: ${data['pnl']:.2f}) [LIVE]")
                    else:
                        logger.info("   📊 No Live positions")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not fetch Live positions: {e}")
            
            # ========== PHASE 5: AUTORESEARCH (Hourly) ==========
            if cycle_count % 12 == 0:  # Every 12 cycles = 1 hour
                logger.info("🔬 Running AutoResearch cycle...")
                try:
                    result = guardian.run_autoresearch_cycle()
                    logger.info(f"   AutoResearch: {result}")
                except Exception as e:
                    logger.error(f"   AutoResearch failed: {e}")
            
            # ========== CYCLE SUMMARY ==========
            cycle_time = time.time() - cycle_start
            logger.info(f"✅ Cycle #{cycle_count} completed in {cycle_time:.1f}s")
            logger.info(f"   Total Trades: {guardian.metrics.total_trades}")
            logger.info(f"   Success Rate: {guardian.metrics.success_rate():.1f}%")
            
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
