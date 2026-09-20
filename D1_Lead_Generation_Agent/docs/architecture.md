# D1 Architecture

```text
                 ┌───────────────┐
                 │   Streamlit   │
                 │  ICP + Results│
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   LangGraph   │
                 │ Orchestrator  │
                 └───────┬───────┘
                         │
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
 Discovery          Enrichment          Scoring
  Agent               Agent              Agent
        │                │                 │
        ▼                ▼                 ▼
    Serper          Allowed pages      Gemini + rubric
        │                │
        ▼                │
 robots.txt ─────────────┘
 urllib.robotparser
        │
        ▼
 Deduplication (Pandas)
        │
        ▼
 SQLite cache / logs
        │
        ▼
 CSV + HubSpot-style CSV
```

## Compliance gate

Discovery may return URLs, but the application does not fetch a result page until `urllib.robotparser` allows it. If robots.txt cannot be read, the application fails closed and skips the URL.
