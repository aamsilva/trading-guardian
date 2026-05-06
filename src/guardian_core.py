#!/usr/bin/env python3
"""
Trading Guardian - Core System
Sistema autónomo de execução a prova de falhas

4 Critical Failure Points Fixed:
FP1: Authentication Failure → Graceful handling + .env template
FP2: Missing Pre-Execution Validation → validation.py
FP3: No Rollback Mechanism → rollback.py  
FP4: No Health Monitoring → monitor.py
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Guardian - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class TradeOrder:
    """Represents a trade order with validation"""
    symbol: str
    side: str  # buy/sell
    quantity: float
    order_type: str = "market"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = "default"
    confidence: float = 0.5  # default confidence
    
    def validate(self) -> Tuple[bool, str]:
        """Validate order parameters"""
        if not self.symbol or len(self.symbol) < 1:
            return False, "Invalid symbol"
        if self.side not in ['buy', 'sell']:
            return False, "Side must be 'buy' or 'sell'"
        if self.quantity <= 0:
            return False, "Quantity must be positive"
        return True, "OK"


@dataclass
class SystemMetrics:
    """System health metrics"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: SystemStatus = SystemStatus.HEALTHY
    health_score: float = 100.0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    api_calls: int = 0
    api_errors: int = 0
    uptime_seconds: float = 0.0
    
    def success_rate(self) -> float:
        if self.total_trades == 0:
            return 100.0
        return (self.successful_trades / self.total_trades) * 100


class TradingGuardian:
    """
    Main Guardian system with AutoResearch integration
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.project_path = "/Volumes/disco1tb/projects/trading-guardian"
        self.config_path = f"{self.project_path}/{config_path}"
        self.config = self._load_config()
        self.metrics = SystemMetrics()
        self.start_time = time.time()
        
        # Core components (lazy loaded)
        self._validator = None
        self._rollback = None
        self._monitor = None
        self._autoresearch = None
        self._strategy_engine = None
        self._alpaca_executor = None
        
        # Credentials check (FP1 fix)
        self.credentials_ok = self._check_credentials()
        
        # Initialize strategy engine and register strategies
        self._init_strategies()
        
        logger.info(f"Trading Guardian initialized | Credentials: {self.credentials_ok}")
    
    def _load_config(self) -> Dict:
        """Load configuration"""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("Config not found, using defaults")
            return self._default_config()
        except Exception as e:
            logger.error(f"Config error: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        return {
            "guardian": {
                "max_risk_per_trade": 0.01,
                "max_daily_loss": 0.05,
                "validation_enabled": True,
                "auto_rollback": True
            },
            "autoresearch": {
                "enabled": True,
                "experiment_interval": 3600
            }
        }
    
    def _check_credentials(self) -> bool:
        """
        Check if API credentials are configured (FP1)
        Uses AlpacaExecutor's credential loading logic
        """
        try:
            # Try to initialize AlpacaExecutor - it will load from ~/.openclaw/secrets/
            from alpaca_executor import AlpacaExecutor
            executor = AlpacaExecutor(use_live=False)
            # If no exception, credentials are OK
            logger.info("✅ Alpaca credentials verified via AlpacaExecutor")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Credentials check failed: {e}")
            return False
    
    @property
    def validator(self):
        """Lazy load validator (FP2)"""
        if self._validator is None:
            from validation import PreExecutionValidator
            self._validator = PreExecutionValidator(self)
        return self._validator
    
    @property
    def rollback(self):
        """Lazy load rollback (FP3)"""
        if self._rollback is None:
            from rollback import RollbackManager
            self._rollback = RollbackManager(self)
        return self._rollback
    
    @property
    def monitor(self):
        """Lazy load monitor (FP4)"""
        if self._monitor is None:
            from monitor import HealthMonitor
            self._monitor = HealthMonitor(self)
        return self._monitor
    
    @property
    def autoresearch(self):
        """Lazy load AutoResearch engine"""
        if self._autoresearch is None:
            from autoresearch_engine import AutoResearchEngine
            self._autoresearch = AutoResearchEngine(self.project_path)
        return self._autoresearch
    
    @property
    def strategy_engine(self):
        """Lazy load Strategy Engine (multi-strategy)"""
        if self._strategy_engine is None:
            from strategy_engine import StrategyEngine
            from strategy_bollinger import BollingerStrategy
            from strategy_momentum import MomentumStrategy
            from strategy_rsi import RSIStrategy
            from strategy_first_hour import FirstHourBreakoutStrategy
            
            self._strategy_engine = StrategyEngine()
            self._strategy_engine.register_strategy('bollinger', BollingerStrategy())
            self._strategy_engine.register_strategy('momentum', MomentumStrategy())
            self._strategy_engine.register_strategy('rsi', RSIStrategy())
            self._strategy_engine.register_strategy('first_hour', FirstHourBreakoutStrategy())
            
            logger.info(f"✅ StrategyEngine loaded with {len(self._strategy_engine.strategies)} strategies")
        return self._strategy_engine
    
    @property
    def alpaca_executor(self):
        """Lazy load Alpaca Executor for real trades"""
        if self._alpaca_executor is None:
            from alpaca_executor import AlpacaExecutor
            self._alpaca_executor = AlpacaExecutor(use_live=False)  # Paper trading
            logger.info("✅ AlpacaExecutor initialized (Paper Trading)")
        return self._alpaca_executor
    
    def _init_strategies(self):
        """Initialize and register all trading strategies"""
        try:
            # This will trigger the lazy loading
            _ = self.strategy_engine
        except Exception as e:
            logger.warning(f"Failed to initialize strategies: {e}")
    
    def execute_trade(self, order: TradeOrder) -> Tuple[bool, str, Dict]:
        """
        Execute a trade with full validation and rollback
        Returns: (success, message, details)
        """
        logger.info(f"Executing trade: {order.side} {order.quantity} {order.symbol}")
        self.metrics.total_trades += 1
        self.metrics.api_calls += 1
        
        # Phase1: Validate order
        if self.config.get("guardian", {}).get("validation_enabled", True):
            valid, msg = self.validator.validate_order(order)
            if not valid:
                self.metrics.failed_trades += 1
                logger.error(f"Validation failed: {msg}")
                return False, f"Validation failed: {msg}", {}
        
        # Phase2: Check credentials
        if not self.credentials_ok:
            self.metrics.failed_trades += 1
            return False, "Credentials not configured", {}
        
        # Phase3: Pre-execution snapshot (for rollback)
        snapshot = self.rollback.create_snapshot(f"pre_trade_{order.symbol}")
        
        # Phase4: Execute REAL order via Alpaca
        try:
            result = self._execute_real_order(order)
            
            if result["success"]:
                self.metrics.successful_trades += 1
                logger.info(f"✅ Trade executed: {result}")
                
                # Send Discord notification immediately
                self._notify_discord(order, result, success=True)
                
                return True, "Trade executed successfully", result
            else:
                # Rollback if enabled
                if self.config.get("guardian", {}).get("auto_rollback", True):
                    self.rollback.restore_snapshot(snapshot["id"])
                self.metrics.failed_trades += 1
                
                # Send Discord notification of failure
                self._notify_discord(order, result, success=False)
                
                return False, result.get("error", "Unknown error"), result
                
        except Exception as e:
            self.metrics.failed_trades += 1
            self.metrics.api_errors += 1
            logger.error(f"Trade execution error: {e}")
            
            # Auto-rollback on failure
            if self.config.get("guardian", {}).get("auto_rollback", True):
                self.rollback.restore_snapshot(snapshot["id"])
            
            # Send Discord notification of error
            self._notify_discord(order, {"error": str(e)}, success=False)
            
            return False, f"Exception: {str(e)}", {}
    
    def _execute_real_order(self, order: TradeOrder) -> Dict:
        """
        Execute order via AlpacaExecutor (REAL execution)
        """
        try:
            # Get executor
            executor = self.alpaca_executor
            
            # Submit order
            result = executor.submit_order(
                symbol=order.symbol,
                qty=order.quantity,
                side=order.side,
                order_type=order.order_type
            )
            
            if result:
                filled_price = result.get("filled_avg_price")
                filled_qty = result.get("filled_qty")
                return {
                    "success": True,
                    "order_id": result.get("id"),
                    "symbol": result.get("symbol"),
                    "filled_price": float(filled_price) if filled_price is not None else 0.0,
                    "filled_qty": float(filled_qty) if filled_qty is not None else 0.0,
                    "status": result.get("status"),
                    "strategy": order.strategy
                }
            else:
                return {
                    "success": False,
                    "error": "Order submission failed - no result returned"
                }
                
        except Exception as e:
            logger.error(f"Real execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_real_trade(self, signal: Dict) -> Tuple[bool, str]:
        """
        Execute a trade from a strategy signal
        signal: Dict with keys: symbol, qty, side, strategy_name, confidence
        Returns: (success, message)
        """
        order = TradeOrder(
            symbol=signal["symbol"],
            side=signal.get("side", "buy"),
            quantity=signal["qty"],
            order_type="market",
            strategy=signal.get("strategy_name", "unknown"),
            confidence=signal.get("confidence", 0.5)
        )
        
        success, msg, details = self.execute_trade(order)
        return success, msg
    
    def aggregate_signals(self) -> List[Dict]:
        """
        Aggregate signals from all strategies
        Returns: List of trade signals ready for execution
        """
        try:
            # Build prices dict for strategy engine
            # Include current positions + default symbols
            prices = {}
            
            # Get current positions
            positions = self.alpaca_executor.get_positions()
            if positions:
                for symbol, data in positions.items():
                    qty = data.get('qty', 0)
                    current_price = data.get('current')
                    if current_price:
                        prices[symbol] = {"qty": qty, "current": current_price}
            
            # Add default symbols to monitor (even without positions)
            default_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
            for sym in default_symbols:
                if sym not in prices:
                    current_price = self.alpaca_executor.get_current_price(sym)
                    if current_price:
                        prices[sym] = {"qty": 0, "current": current_price}
            
            if not prices:
                logger.warning("No price data available for any symbol")
                return []
            
            # Get all signals from strategy engine
            all_signals = self.strategy_engine.get_all_signals(prices)
            
            # Aggregate using strategy_engine's aggregation
            aggregated = self.strategy_engine.aggregate_signals(all_signals)
            
            # Convert to trade signals
            trades = []
            for symbol, agg in aggregated.items():
                if agg["buy_votes"] > agg["sell_votes"]:
                    # Calculate quantity based on confidence and account balance
                    try:
                        account = self.alpaca_executor.get_account()
                        if account:
                            cash = float(account.get("cash", 0))
                            # Risk 2% of cash per trade
                            max_trade_value = cash * 0.02
                            current_price = self.alpaca_executor.get_current_price(symbol)
                            if current_price and current_price > 0:
                                qty = round(max_trade_value / current_price, 4)
                                if qty > 0:
                                    trades.append({
                                        "symbol": symbol,
                                        "qty": qty,
                                        "side": "buy",
                                        "strategy_name": "aggregated",
                                        "confidence": agg.get("confidence", 0.5),
                                        "buy_votes": agg["buy_votes"],
                                        "sell_votes": agg["sell_votes"]
                                    })
                    except Exception as e:
                        logger.error(f"Error calculating trade size for {symbol}: {e}")
            
            logger.info(f"Aggregated {len(trades)} buy signals from strategies")
            return trades
            
        except Exception as e:
            logger.error(f"Signal aggregation error: {e}")
            return []
    
    def _notify_discord(self, order: TradeOrder, result: Dict, success: bool):
        """
        Send immediate Discord notification after trade execution
        """
        try:
            from discord_retry import send_trade_notification
            
            notification_data = {
                "symbol": order.symbol,
                "qty": order.quantity,
                "price": result.get("filled_price", 0),
                "strategy_name": order.strategy,
                "confidence": getattr(order, "confidence", 0.5),
                "side": order.side
            }
            
            send_trade_notification(notification_data, success, result)
            
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
    
    def _simulate_execution(self, order: TradeOrder) -> Dict:
        """Simulate trade execution (DEPRECATED - use _execute_real_order)"""
        time.sleep(0.5)  # Simulate API call
        return {
            "success": True,
            "order_id": f"sim_{int(time.time())}",
            "symbol": order.symbol,
            "filled_price": 100.0,  # Simulated
            "filled_qty": order.quantity,
            "status": "filled"
        }
    
    def run_autoresearch_cycle(self) -> Dict:
        """Run one AutoResearch cycle"""
        if not self.config.get("autoresearch", {}).get("enabled", True):
            return {"status": "disabled"}
        
        logger.info("🔬 Starting AutoResearch cycle...")
        return self.autoresearch.run_cycle()
    
    def get_health(self) -> Dict:
        """Get current system health"""
        self.metrics.uptime_seconds = time.time() - self.start_time
        return self.monitor.check_health()
    
    def run_forever(self, check_interval: int = 60):
        """
        Main loop - continuous operation with AutoResearch
        """
        logger.info("🚀 Trading Guardian entering main loop...")
        self.metrics.status = SystemStatus.HEALTHY
        
        last_autoresearch = 0
        interval = self.config.get("autoresearch", {}).get("experiment_interval", 3600)
        
        while True:
            try:
                # Health check
                health = self.get_health()
                
                # Run AutoResearch periodically
                if time.time() - last_autoresearch > interval:
                    cycle_result = self.run_autoresearch_cycle()
                    logger.info(f"AutoResearch cycle: {cycle_result}")
                    last_autoresearch = time.time()
                
                # Log status
                logger.info(
                    f"Status: {self.metrics.status.value} | "
                    f"Health: {self.metrics.health_score:.1f} | "
                    f"Trades: {self.metrics.total_trades} | "
                    f"Success: {self.metrics.success_rate():.1f}%"
                )
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self.metrics.status = SystemStatus.CRITICAL
                time.sleep(check_interval)


if __name__ == "__main__":
    import os
    guardian = TradingGuardian()
    
    # Test with a sample order
    order = TradeOrder(
        symbol="AAPL",
        side="buy",
        quantity=10,
        stop_loss=95.0,
        take_profit=110.0
    )
    
    success, msg, details = guardian.execute_trade(order)
    print(f"Trade result: {success} - {msg}")
    
    # Health check
    health = guardian.get_health()
    print(f"Health: {json.dumps(health, indent=2)}")
