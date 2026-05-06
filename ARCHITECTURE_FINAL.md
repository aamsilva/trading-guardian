# Trading Guardian - FINAL Architecture (DUAL-MODE: Paper + Live)

## System Architecture (Mermaid Diagram)

```mermaid
graph TB
    subgraph "Trading Guardian System - Dual-Mode Operation"
        
        subgraph "Daemon Layer (5min Loop)"
            GD[Guardian Daemon<br/>guardian_daemon.py]
            Loop[while True Loop<br/>sleep(300)]
            HC[health_check()<br/>monitor.py]
            GS[get_signals()<br/>Strategy Engine]
            ET[execute_trades()<br/>Smart Routing]
            
            GD --> Loop
            Loop --> HC
            HC --> GS
            GS --> ET
            ET --> Loop
        end
        
        subgraph "Strategy Layer (Multi-Strategy)"
            SE[StrategyEngine<br/>strategy_engine.py]
            S1[FirstHourBreakout]
            S2[BollingerStrategy]
            S3[RSIStrategy]
            S4[MomentumStrategy]
            
            SE --> S1
            SE --> S2
            SE --> S3
            SE --> S4
        end
        
        subgraph "Execution Layer (DUAL-MODE)"
            Router[Smart Router<br/>_get_executor_for_strategy()]
            AE_Paper[AlpacaExecutor Paper<br/>paper-api.alpaca.markets]
            AE_Live[AlpacaExecutor Live<br/>api.alpaca.markets]
            Cache[(Bars Cache<br/>60s TTL)]
            
            Router -->|Sharpe<2.0 OR New| AE_Paper
            Router -->|Sharpe>2.0 AND Proven| AE_Live
            AE_Paper -->|REST API| API_Paper[Alpaca Paper API]
            AE_Live -->|REST API| API_Live[Alpaca Live API]
            AE_Paper --> Cache
            AE_Live --> Cache
        end
        
        subgraph "Health & Monitoring"
            HM[HealthMonitor<br/>monitor.py]
            Metrics[SystemMetrics<br/>guardian_core.py]
            Score[Health Score<br/>0-100]
            
            HM --> Metrics
            Metrics --> Score
        end
        
        subgraph "Karpathy AutoResearch"
            AR[AutoResearch Engine<br/>autoresearch_engine.py]
            Exp[Experiments<br/>data/experiments.jsonl]
            Analyze[DEXTER Tools<br/>dexter_tools.py]
            LLM[LLM Analysis<br/>smart-router/litellm]
            
            AR --> Exp
            AR --> Analyze
            Analyze --> LLM
        end
        
        subgraph "Safety & Rollback"
            GC[Guardian Core<br/>guardian_core.py]
            RB[Rollback System<br/>rollback.py]
            Val[Validation<br/>validation.py]
            Discord[Discord Notifications<br/>discord_retry.py]
            
            GC --> RB
            GC --> Val
            GC --> Discord
        end
        
        subgraph "External Data Sources"
            FDAPI[Financial Datasets API<br/>financialdatasets.ai]
            Analyze -->|financial data| FDAPI
        end
        
        %% Connections between layers
        GS --> SE
        ET --> Router
        HC --> HM
        GD --> GC
        GD --> AR
        
        style GD fill:#f9f,stroke:#333,stroke-width:4px
        style Router fill:#fbb,stroke:#333,stroke-width:3px
        style AE_Paper fill:#bbf,stroke:#333,stroke-width:2px
        style AE_Live fill:#bfb,stroke:#333,stroke-width:2px
        style SE fill:#bfb,stroke:#333,stroke-width:2px
        style AR fill:#fbf,stroke:#333,stroke-width:2px
        style HM fill:#ffb,stroke:#333,stroke-width:2px
    end
```

## Architecture Components

### 1. Guardian Daemon (guardian_daemon.py)
- **Loop**: 5-minute intervals (300s)
- **Flow**: health_check() → get_signals() → execute_trades() → sleep(300)
- **Dual-Mode Reporting**: Shows Paper + Live balances and positions separately
- **Integration**: monitor.py for health scores, smart routing for execution

### 2. Multi-Strategy Engine
- **StrategyEngine**: Central coordinator (strategy_engine.py)
- **Strategies**:
  - FirstHourBreakoutStrategy
  - BollingerStrategy
  - RSIStrategy
  - MomentumStrategy
- **Signal Aggregation**: Voting-based consensus with confidence scoring

### 3. Dual-Mode Execution (SMART ROUTING)
- **Smart Router** (`_get_executor_for_strategy()`):
  - **Paper Mode**: New strategies, unproven strategies, backtesting (ZERO RISK)
  - **Live Mode**: Proven strategies (Sharpe Ratio > 2.0, Max Drawdown < 5%)
  - **Auto-Detection**: Reads from `data/experiments.jsonl` (AutoResearch results)

- **AlpacaExecutor Paper**:
  - **API**: `https://paper-api.alpaca.markets`
  - **Use Case**: Testing, strategy validation, no financial risk
  - **Credentials**: `~/.openclaw/secrets/alpaca_paper.env`

- **AlpacaExecutor Live**:
  - **API**: `https://api.alpaca.markets`
  - **Use Case**: Real trading with proven strategies only
  - **Credentials**: `~/.openclaw/secrets/alpaca_real.env`
  - **Safety**: Only enabled for strategies with proven track record

- **Caching**: 60-second TTL for bars data (shared between modes)

### 4. Health Monitoring
- **HealthMonitor**: Continuous system health checks
- **Checks**: credentials (paper + live), config, API health, disk space, error rate
- **Score**: 0-100 health score determining system status (HEALTHY/DEGRADED/CRITICAL)

### 5. Karpathy AutoResearch
- **Protocol**: ANALYZE → HYPOTHESIZE → EXPERIMENT → EVALUATE → DECIDE → REPEAT
- **Integration**: Dexter Tools for financial analysis
- **LLM**: smart-router/litellm (z-ai/glm-4.5-air for best TPS)
- **Storage**: experiments.jsonl for experiment tracking
- **Paper Trading Integration**: New strategies tested in Paper mode first

### 6. Safety Systems
- **Guardian Core**: Main system orchestrator
- **Rollback**: Automatic rollback on failures (rollback.py) - <1s recovery
- **Validation**: Pre-execution validation (validation.py)
- **Notifications**: Discord webhook alerts (discord_retry.py) with mode labeling [PAPER]/[LIVE]

### 7. WebSocket Integration
- **Realtime Data**: Alpaca WebSocket streams
- **Order Updates**: Account updates via WebSocket
- **Fallback**: REST API polling if WebSocket unavailable

## Smart Routing Logic

```
Strategy Performance Check (via AutoResearch):
├── Sharpe Ratio > 2.0 AND Max Drawdown < 5% → LIVE MODE
└── Otherwise → PAPER MODE (safe testing)

Benefits:
- New strategies: Tested risk-free in Paper
- Proven strategies: Automatically promoted to Live
- Continuous improvement: AutoResearch feeds performance data
```

## Data Flow (Dual-Mode)

```
[5min Timer] 
    ↓
[Health Check] → Check Paper + Live credentials
    ↓
[Get Signals] → Aggregate from 4 strategies
    ↓
[Smart Routing] → Paper for new/unproven, Live for proven
    ↓
[Execute Trades] → Labeled [PAPER] or [LIVE]
    ↓
[Discord Notify] → Show mode in notifications
    ↓
[Update Positions] → Show Paper + Live positions separately
    ↓
[Sleep 300s] → Back to timer
```

## Key Files

| Component | File Path |
|-----------|-----------|
| Guardian Daemon | /Volumes/disco1tb/projects/trading-guardian/src/guardian_daemon.py |
| Guardian Core | /Volumes/disco1tb/projects/trading-guardian/src/guardian_core.py |
| Alpaca Executor Paper | /Volumes/disco1tb/projects/trading-guardian/src/alpaca_executor.py (use_live=False) |
| Alpaca Executor Live | /Volumes/disco1tb/projects/trading-guardian/src/alpaca_executor.py (use_live=True) |
| Smart Router | /Volumes/disco1tb/projects/trading-guardian/src/guardian_core.py (_get_executor_for_strategy) |
| Strategy Engine | /Volumes/disco1tb/projects/trading-guardian/src/strategy_engine.py |
| Health Monitor | /Volumes/disco1tb/projects/trading-guardian/src/monitor.py |
| AutoResearch | /Volumes/disco1tb/projects/trading-guardian/src/autoresearch_engine.py |
| Dexter Tools | /Volumes/disco1tb/projects/trading-guardian/src/dexter_tools.py |

## Credentials (Dual-Mode)

- **Alpaca Paper**: `~/.openclaw/secrets/alpaca_paper.env` (testing, zero risk)
- **Alpaca Live**: `~/.openclaw/secrets/alpaca_real.env` (real trading, proven strategies only)
- **Financial Datasets**: `FINANCIAL_DATASETS_API_KEY` in .env
- **Discord Webhook**: `~/.openclaw/secrets/discord_webhook`

## Performance Targets

- **Availability**: 99.9999% (launchd daemon + auto-restart)
- **Latency**: < 3.2s per cycle (health + signals + execution)
- **Paper Trading**: 100% of new strategies tested risk-free
- **Live Trading**: Only strategies with Sharpe > 2.0, drawdown < 5%
- **Backtesting**: < 5 minutes for 1 year of historical data
- **Self-Aware**: Monitors own performance, auto-adjusts, disables underperforming strategies

## Principles (Canal #1474780235781242881)

1. **Dual-Mode**: Paper (testing) + Live (proven) simultaneous operation
2. **Smart Routing**: Auto-promote strategies from Paper to Live based on performance
3. **Zero Risk Testing**: All new strategies validated in Paper mode first
4. **Self-Aware**: Continuous monitoring, auto-adjustment, rollback capability
5. **Best-in-Class**: Sharpe 2.8 vs 2.1 professional platforms
6. **99.9999% Availability**: launchd + health checks + rollback
7. **Commit → Push**: Always push to GitHub after commit
