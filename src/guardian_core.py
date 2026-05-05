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
        
        # Credentials check (FP1 fix)
        self.credentials_ok = self._check_credentials()
        
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
        """Check if API credentials are configured (FP1)"""
        env_path = f"{self.project_path}/.env"
        if not os.path.exists(env_path):
            logger.warning("⚠️  No .env file found - create from config/.env.template")
            return False
        
        # Check for required vars
        required = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY']
        missing = []
        with open(env_path, 'r') as f:
            content = f.read()
            for var in required:
                if var not in content:
                    missing.append(var)
        
        if missing:
            logger.warning(f"⚠️  Missing credentials: {missing}")
            return False
        
        return True
    
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
    
    def execute_trade(self, order: TradeOrder) -> Tuple[bool, str, Dict]:
        """
        Execute a trade with full validation and rollback
        Returns: (success, message, details)
        """
        logger.info(f"Executing trade: {order.side} {order.quantity} {order.symbol}")
        self.metrics.total_trades += 1
        self.metrics.api_calls += 1
        
        # Phase 1: Validate order
        if self.config.get("guardian", {}).get("validation_enabled", True):
            valid, msg = self.validator.validate_order(order)
            if not valid:
                self.metrics.failed_trades += 1
                logger.error(f"Validation failed: {msg}")
                return False, f"Validation failed: {msg}", {}
        
        # Phase 2: Check credentials
        if not self.credentials_ok:
            self.metrics.failed_trades += 1
            return False, "Credentials not configured", {}
        
        # Phase 3: Pre-execution snapshot (for rollback)
        snapshot = self.rollback.create_snapshot(f"pre_trade_{order.symbol}")
        
        # Phase 4: Execute (simulated - no real API without credentials)
        try:
            # In real implementation: call Alpaca API
            result = self._simulate_execution(order)
            
            if result["success"]:
                self.metrics.successful_trades += 1
                logger.info(f"✅ Trade executed: {result}")
                return True, "Trade executed successfully", result
            else:
                # Rollback if enabled
                if self.config.get("guardian", {}).get("auto_rollback", True):
                    self.rollback.restore_snapshot(snapshot["id"])
                self.metrics.failed_trades += 1
                return False, result.get("error", "Unknown error"), result
                
        except Exception as e:
            self.metrics.failed_trades += 1
            self.metrics.api_errors += 1
            logger.error(f"Trade execution error: {e}")
            
            # Auto-rollback on failure
            if self.config.get("guardian", {}).get("auto_rollback", True):
                self.rollback.restore_snapshot(snapshot["id"])
            
            return False, f"Exception: {str(e)}", {}
    
    def _simulate_execution(self, order: TradeOrder) -> Dict:
        """Simulate trade execution (replace with real API)"""
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
