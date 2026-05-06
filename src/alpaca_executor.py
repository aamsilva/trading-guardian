#!/usr/bin/env python3
"""
Alpaca Executor - Real Execution Layer for Trading Guardian
Paper trading via Alpaca API with 60s cache for bars

Uses requests library (consistent with alpha_trade/alpaca_client.py)
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class AlpacaExecutor:
    """
    Executor for real trading operations via Alpaca API
    Paper trading by default: https://paper-api.alpaca.markets
    """
    
    def __init__(self, use_live=False):
        """
        Initialize Alpaca executor
        
        Args:
            use_live: If True, use live trading API. If False, use paper trading.
        """
        self.use_live = use_live
        self.load_credentials()
        
        # Set base URL based on live/paper mode
        if use_live:
            self.base_url = "https://api.alpaca.markets"
        else:
            self.base_url = "https://paper-api.alpaca.markets"
        
        self.data_url = "https://data.alpaca.markets"
        
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret
        }
        
        # Cache for bars data (60 second TTL)
        self._price_cache = {}
        self._cache_ttl = 60  # 60 seconds cache
        
        # Trading state
        self.max_position_value = 500  # Max $500 per position
        self.min_confidence = 0.7  # Minimum confidence to execute
        
    def load_credentials(self):
        """
        Load API credentials from ~/.openclaw/secrets/alpaca_paper.env
        """
        if self.use_live:
            env_path = os.path.expanduser('~/.openclaw/secrets/alpaca_real.env')
        else:
            env_path = os.path.expanduser('~/.openclaw/secrets/alpaca_paper.env')
        
        # Load from .env file
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        try:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip()
                        except ValueError:
                            pass
        
        # Get credentials from environment
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.secret = os.environ.get('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret:
            raise ValueError(
                f"Missing Alpaca credentials. "
                f"Please check {env_path} contains ALPACA_API_KEY and ALPACA_SECRET_KEY"
            )
    
    def get_account(self) -> Optional[Dict]:
        """
        Get account information
        
        Returns:
            Account dict or None if error
        """
        try:
            resp = requests.get(
                f"{self.base_url}/v2/account",
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error getting account: {e}")
        return None
    
    def get_positions(self) -> Dict:
        """
        Get current positions
        
        Returns:
            Dict of {symbol: {qty, current, avg_entry, pnl}}
        """
        try:
            resp = requests.get(
                f"{self.base_url}/v2/positions",
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                return {
                    p['symbol']: {
                        'qty': float(p['qty']),
                        'current': float(p['current_price']),
                        'avg_entry': float(p['avg_entry_price']),
                        'pnl': float(p['unrealized_pl'])
                    }
                    for p in resp.json()
                    if float(p['qty']) > 0
                }
        except Exception as e:
            print(f"Error getting positions: {e}")
        return {}
    
    def get_bars(self, symbol: str, period: int = 30, feed: str = 'iex') -> List[Dict]:
        """
        Get historical bars with 60-second cache
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            period: Number of bars to retrieve
            feed: Data feed ('iex' or 'sip')
        
        Returns:
            List of bar dicts with keys: t, o, h, l, c, v
        """
        cache_key = f"bars_{symbol}_{period}_{feed}"
        now = time.time()
        
        # Check cache
        if cache_key in self._price_cache:
            cached = self._price_cache[cache_key]
            if now - cached['timestamp'] < self._cache_ttl:
                return cached['data']
        
        try:
            end = datetime.now()
            start = end - timedelta(days=period + 10)
            
            params = {
                'start': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'timeframe': '1Day',
                'limit': period + 5,
                'feed': feed
            }
            
            resp = requests.get(
                f"{self.data_url}/v2/stocks/{symbol}/bars",
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                bars = resp.json().get('bars', [])
                # Cache result
                self._price_cache[cache_key] = {
                    'timestamp': now,
                    'data': bars
                }
                return bars
            else:
                print(f"API error for {symbol}: {resp.status_code}")
        except Exception as e:
            print(f"Error getting bars for {symbol}: {e}")
        
        return []
    
    def calculate_bollinger_bands(self, symbol: str, period: int = 30, std_dev: float = 2.5) -> Optional[Dict]:
        """
        Calculate Bollinger Bands using cached bars
        
        Args:
            symbol: Stock symbol
            period: Lookback period
            std_dev: Number of standard deviations
        
        Returns:
            Dict with keys: upper, middle, lower, current
        """
        bars = self.get_bars(symbol, period)
        
        if len(bars) < 5:  # Need at least a few bars
            return None
        
        use_bars = min(len(bars), period)
        closes = [float(b['c']) for b in bars[-use_bars:]]
        
        if not closes:
            return None
        
        mean = sum(closes) / len(closes)
        variance = sum((x - mean) ** 2 for x in closes) / len(closes)
        std = variance ** 0.5
        
        return {
            'upper': mean + (std_dev * std),
            'middle': mean,
            'lower': mean - (std_dev * std),
            'current': closes[-1]
        }
    
    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = 'market') -> Optional[Dict]:
        """
        Submit an order to Alpaca
        
        Args:
            symbol: Stock symbol
            qty: Quantity to buy/sell
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', etc.
        
        Returns:
            Order dict or None if error
        """
        try:
            # Determine appropriate time_in_force
            # For fractional orders, Alpaca requires 'day'
            tif = 'day' if qty % 1 != 0 else 'gtc'
            
            data = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': tif
            }
            
            resp = requests.post(
                f"{self.base_url}/v2/orders",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                order = resp.json()
                print(f"✅ Order submitted: {side} {qty} {symbol} @ {order.get('filled_avg_price', 'market')}")
                return order
            else:
                print(f"❌ Order failed: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"Error submitting order: {e}")
        
        return None
    
    def get_orders(self, status: str = 'all', limit: int = 100) -> List[Dict]:
        """
        Get orders (filled, pending, etc.)
        
        Args:
            status: 'open', 'closed', 'all'
            limit: Maximum number of orders to return
        
        Returns:
            List of order dicts
        """
        try:
            params = {'status': status, 'limit': limit}
            resp = requests.get(
                f"{self.base_url}/v2/orders",
                params=params,
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error getting orders: {e}")
        return []
    
    def cancel_all_orders(self) -> bool:
        """
        Cancel all open orders
        
        Returns:
            True if successful, False otherwise
        """
        try:
            resp = requests.delete(
                f"{self.base_url}/v2/orders",
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                print("✅ All orders cancelled")
                return True
        except Exception as e:
            print(f"Error cancelling orders: {e}")
        return False
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol using latest bar
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Current price or None
        """
        bars = self.get_bars(symbol, period=5)
        if bars:
            return float(bars[-1]['c'])
        return None


# Singleton pattern for easy access
_executor_paper = None
_executor_live = None


def get_executor(use_live=False) -> AlpacaExecutor:
    """
    Get or create AlpacaExecutor singleton
    
    Args:
        use_live: If True, return live trading executor
    
    Returns:
        AlpacaExecutor instance
    """
    global _executor_paper, _executor_live
    
    if use_live:
        if _executor_live is None:
            _executor_live = AlpacaExecutor(use_live=True)
        return _executor_live
    else:
        if _executor_paper is None:
            _executor_paper = AlpacaExecutor(use_live=False)
        return _executor_paper


if __name__ == "__main__":
    # Test the executor
    print("Testing AlpacaExecutor...")
    
    executor = get_executor(use_live=False)
    
    # Test account
    print("\n✅ Getting account info...")
    account = executor.get_account()
    if account:
        print(f"  Account ID: {account.get('id')}")
        print(f"  Cash: ${float(account.get('cash', 0)):.2f}")
        print(f"  Buying Power: ${float(account.get('buying_power', 0)):.2f}")
    
    # Test positions
    print("\n✅ Getting positions...")
    positions = executor.get_positions()
    print(f"  Positions: {len(positions)}")
    for sym, data in positions.items():
        print(f"  {sym}: {data['qty']} shares @ ${data['current']:.2f}")
    
    # Test Bollinger Bands
    print("\n✅ Calculating Bollinger Bands for AAPL...")
    bb = executor.calculate_bollinger_bands('AAPL')
    if bb:
        print(f"  Upper: ${bb['upper']:.2f}")
        print(f"  Middle: ${bb['middle']:.2f}")
        print(f"  Lower: ${bb['lower']:.2f}")
        print(f"  Current: ${bb['current']:.2f}")
    else:
        print("  Failed to calculate")


# Compatibility: Alpha Trade strategies expect get_client()
def get_client(use_live=False):
    """
    Compatibility function for Alpha Trade strategies
    Returns AlpacaExecutor instance (same as get_executor)
    """
    return get_executor(use_live=use_live)
