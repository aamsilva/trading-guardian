# Trading Guardian Architecture

## AutoResearch Protocol (Karpathy-style)
1. Analyze current system state
2. Generate hypothesis for improvement
3. Execute controlled experiment
4. Evaluate results
5. Decide: KEEP (merge) or REVERT (discard)
6. Repeat

## 4 Critical Failure Points (to fix)
TBD - identified during first experiment cycle

## Safety Mechanisms
- Pre-execution validation
- Automatic rollback on failure
- Separate experiment branches
- Resource limits
