# Current Project Graph

This graph describes the verified current checkout, not the future product architecture.

```text
Browser
  └─ React/Vite frontend (port 8080)
       ├─ static dashboard and route placeholders
       └─ fetch with VITE_API_URL
            └─ FastAPI backend (port 8000)
                 ├─ static root, ping, and demo responses
                 └─ scan, analysis, and agentic routes return unavailable responses
```

There are no active edges from the API to ML inference, PostgreSQL, object storage, authentication, RAG, weather, recommendations, or a production LLM workflow. `PROJECT_BRAIN/11_AUDIT.md` lists current statuses and verification limits. `PROJECT_BRAIN/06_RAG_GRAPH.md` and other future-oriented graphs are plans only.
