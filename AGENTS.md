# Project Context & Agent Rules: South Bend Events Scraper V2

## 🆔 Project Identity
- **Project ID**: `southbendeventsscraperv2`
- **Obsidian Vault Path**: `C:\Users\brian\Documents\Antigravity\Obsidian Context Vault`
- **Project MOC Note**: `[[02-Projects/SouthBendEventsScraperV2/_index|South Bend Events Scraper V2]]`

---

## 🧭 Agent Lifecycle & Memory Protocol

### 1. Inception & Planning (Pulling Context)
- Before implementing major changes or drafting architecture, check the Obsidian Vault for existing specs and decisions:
  - **MOC**: Search for `project_id: "southbendeventsscraperv2"` or inspect `02-Projects/SouthBendEventsScraperV2/_index.md`.
  - **ADRs**: Read `02-Projects/SouthBendEventsScraperV2/architecture/` to align with established decisions.
  - **Knowledge**: Reference shared patterns in `03-Knowledge/`.

### 2. Implementation Guidelines
- Ensure scraper pipeline outputs clean JSON and calendar feeds without duplicates.
- Handle network retries and HTTP rate limits gracefully.
- Reference shared scraping guidelines in `[[03-Knowledge/Tools-Libraries/Python-Scraping-Cron]]`.

### 3. Handoff & Session Logging (Recording Context)
- When completing significant architectural pivots or new subsystem integrations:
  - Create a new ADR note via CLI:
    ```bash
    python "C:\Users\brian\Documents\Antigravity\Obsidian Context Vault\vault_tools.py" add-adr --project "southbendeventsscraperv2" --title "New Architecture Decision"
    ```
  - Append a session summary to project logs and daily activity:
    ```bash
    python "C:\Users\brian\Documents\Antigravity\Obsidian Context Vault\vault_tools.py" add-log --project "southbendeventsscraperv2" --entry "Implemented X and verified Y" --summary "Feature Milestone"
    ```