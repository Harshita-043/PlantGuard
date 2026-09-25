# PlantGuard AI — Project Overview

PlantGuard AI is currently a React/Vite frontend and FastAPI backend shell. Backend email/password authentication now exists, but the frontend is not connected and authorization/ownership checks are not implemented. Real plant diagnosis, plant/scan persistence, integrated image storage, and an active LLM workflow are still unavailable. Private local, Supabase Storage, and Cloudflare R2 adapters exist behind a storage interface, but no API flow currently uses them.

The root `ml/` directory contains model artifacts. Their inference integration with the application is **NOT VERIFIED**; application code must not claim or fabricate ML results.

## Source of truth

- [01_ARCHITECTURE.md](01_ARCHITECTURE.md): verified application architecture
- [05_API_CONTRACTS.md](05_API_CONTRACTS.md): actual current HTTP routes and unavailable operations
- [07_AGENT_GRAPH.md](07_AGENT_GRAPH.md): partial agentic implementation state
- [11_AUDIT.md](11_AUDIT.md): audit findings, changes, test limitations, blockers
- [12_CHANGELOG.md](12_CHANGELOG.md): dated change history and audit correction
- [MANUAL_SETUP.md](../MANUAL_SETUP.md): single local/manual setup guide

Other graph documents describe research or future scope only where they explicitly say so. Documentation alone does not establish implementation.
