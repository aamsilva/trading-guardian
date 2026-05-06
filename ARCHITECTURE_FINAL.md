# Trading Guardian - FINAL Architecture

## System Architecture (Mermaid Diagram)

```mermaid
graph TB
    subgraph "Trading Guardian System - Tier-1 Trading Grade"
        
        subgraph "Daemon Layer (5min Loop)"
            GD[Guardian Daemon<br/>guardian_daemon.py]
            Loop[while True Loop<br/>sleep(300)]
            HC[health_check()<br/>monitor.py]
            GS[get_signals()<br/>Strategy Engine]
            ET[execute_trades()<br/>alpaca_executor.py]
            
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
        
        subgraph "Execution Layer (Real Execution)"
            AE[AlpacaExecutor<br/>alpaca_executor.py]
            API[Alpaca Paper API<br/>paper-api.alpaca.markets]
            WS[WebSocket Stream<br/>realtime data]
            
            AE -->|REST API| API
            AE -->|Cache 60s| Cache[(Bars Cache)]
            WS -->|realtime prices| AE
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
        ET --> AE
        HC --> HM
        GD --> GC
        GD --> AR
        
        style GD fill:#f9f,stroke:#333,stroke-width:4px
        style AE fill:#bbf,stroke:#333,stroke-width:2px
        style SE fill:#bfb,stroke:#333,stroke-width:2px
        style AR fill:#fbf,stroke:#333,stroke-width:2px
        style HM fill:#ffb,stroke:#333,stroke-width:2px
    end
```

## Architecture Components

### 1. Guardian Daemon (guardian_daemon.py)
- **Loop**: 5-minute intervals (300s)
- **Flow**: health_check() → get_signals() → execute_trades() → sleep(300)
- **Integration**: monitor.py for health scores, alpaca_executor.py for execution

### 2. Multi-Strategy Engine
- **StrategyEngine**: Central coordinator (strategy_engine.py)
- **Strategies**:
  - FirstHourBreakoutStrategy
  - BollingerStrategy
  - RSIStrategy
  - MomentumStrategy
- **Signal Aggregation**: Voting-based consensus with confidence scoring

### 3. Real Execution (alpaca_executor.py)
- **API**: Alpaca Paper Trading (https://paper-api.alpaca.markets)
- **Methods**: submit_order(), get_positions(), get_bars(), calculate_bollinger_bands()
- **Caching**: 60-second TTL for bars data
- **Credentials**: Loaded from ~/.openclaw/secrets/alpaca_paper.env

### 4. Health Monitoring
- **HealthMonitor**: Continuous system health checks
- **Checks**: credentials, config, API health, disk space, error rate
- **Score**: 0-100 health score determining system status (HEALTHY/DEGRADED/CRITICAL)

### 5. Karpathy AutoResearch
- **Protocol**: ANALYZE → HYPOTHESIZE → EXPERIMENT → EVALUATE → DECIDE → REPEAT
- **Integration**: Dexter Tools for financial analysis
- **LLM**: smart-router/litellm (NO direct Claude/OpenAI)
- **Storage**: experiments.jsonl for experiment tracking

### 6. Safety Systems
- **Guardian Core**: Main system orchestrator
- **Rollback**: Automatic rollback on failures (rollback.py)
- **Validation**: Pre-execution validation (validation.py)
- **Notifications**: Discord webhook alerts (discord_retry.py)

### 7. WebSocket Integration
- **Realtime Data**: Alpaca WebSocket streams (alpha_trade_websocket.py)
- **Order Updates**: Account updates via WebSocket (alpha_trade_order_watcher.py)
- **Fallback**: REST API polling if WebSocket unavailable

## Data Flow

```
[5min Timer] → [Health Check] → [Get Signals from Strategies] → [Execute Trades] → [Discord Notify] → [Sleep]
      ↑                                                                                        ↓
      └────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Files

| Component | File Path |
|-----------|-----------|
| Guardian Daemon | /Volumes/disco1tb/projects/trading-guardian/src/guardian_daemon.py |
| Alpaca Executor | /Volumes/disco1tb/projects/trading-guardian/src/alpaca_executor.py |
| Strategy Engine | /Users/augustosilva/.openclaw/alpha_trade/strategy_engine.py |
| Health Monitor | /Volumes/disco1tb/projects/trading-guardian/src/monitor.py |
| Guardian Core | /Volumes/disco1tb/projects/trading-guardian/src/guardian_core.py |
| AutoResearch | /Volumes/disco1tb/projects/trading-guardian/src/autoresearch_engine.py |
| Dexter Tools | /Volumes/disco1tb/projects/trading-guardian/src/dexter_tools.py |

## Credentials

- **Alpaca Paper**: ~/.openclaw/secrets/alpaca_paper.env
- **Alpaca Live**: ~/.openclaw/secrets/alpaca_real.env
- **Financial Datasets**: FINANCIAL_DATASETS_API_KEY in .env
- **Discord Webhook**: ~/.openclaw/secrets/discord_webhook
