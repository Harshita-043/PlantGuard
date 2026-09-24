# PlantGuard AI — Project Overview

PlantGuard AI is currently a React/Vite frontend and FastAPI backend shell. It does not currently provide real plant diagnosis, authentication, user/plant/scan persistence, object storage, or an active LLM workflow.

The root `ml/` directory contains model artifacts. Their inference integration with the application is **NOT VERIFIED**; application code must not claim or fabricate ML results.

## Source of truth

- [01_ARCHITECTURE.md](01_ARCHITECTURE.md): verified application architecture
- [05_API_CONTRACTS.md](05_API_CONTRACTS.md): actual current HTTP routes and unavailable operations
- [07_AGENT_GRAPH.md](07_AGENT_GRAPH.md): partial agentic implementation state
- [11_AUDIT.md](11_AUDIT.md): audit findings, changes, test limitations, blockers
- [12_CHANGELOG.md](12_CHANGELOG.md): dated change history and audit correction
- [MANUAL_SETUP.md](../MANUAL_SETUP.md): single local/manual setup guide

Other graph documents describe research or future scope only where they explicitly say so. Documentation alone does not establish implementation.
