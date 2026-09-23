# Market Reader Adapter Contract

This folder is an optional external-input bridge for the V8 Tactical Engine.

## Goal
Market Reader is treated as an external second eye only. It must not override internal V8 technical logic by itself.

## Expected inbox schema
`market_reader/inbox.csv`

Columns:
- `symbol` — e.g. ETH, SOL, LINK, ONDO
- `timeframe` — expected: 1H, 4H, 1D
- `signal` — accepted values: GREEN_DOT, LONG, BUY, RED_DOT, SHORT, SELL, NEUTRAL, WAIT
- `strength` — optional numeric 0-10; blank allowed
- `source_timestamp_utc` — when Market Reader generated the signal
- `received_timestamp_utc` — when the signal reached this bridge
- `source_note` — optional free text

## Safety rules
- Unknown symbols/timeframes/signals are rejected from active scoring.
- Stale signals are ignored for confluence.
- 1H signal max age: 2 hours.
- 4H signal max age: 8 hours.
- 1D signal max age: 48 hours.
- External signal contributes at most +/-2 points to a research confluence score.
- Missing Market Reader data does not block the internal tactical engine.
- Market Reader cannot create a trade signal when the internal engine is NO_TRADE or NO_TRADE_FOMO.
- Output remains research-only and not execution-connected.

## Normalized direction score
- GREEN_DOT / LONG / BUY = +1 direction
- RED_DOT / SHORT / SELL = -1 direction
- NEUTRAL / WAIT = 0

`strength` only affects confidence metadata; it does not turn Market Reader into a standalone decision engine.
