# AI Agent Operating Instructions (South Bend Events Scraper V2)

Welcome, AI assistant. You are collaborating on the **South Bend Events Scraper V2** codebase.

Follow these mandatory directives whenever you begin a session or make changes:

---

## 1. Prime Directives & Architectural North Star

1. **The Single Source of Truth:**
   * All architectural rules, specifications, and formulas are governed by [docs/DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md).
   * Before implementing any feature or modifying existing components, **read `docs/DESIGN_DOCUMENT.md`** and ensure your solution strictly adheres to it.
2. **Obsidian Vault Alignment:**
   * This project is tracked in the master Obsidian Context Vault at:
     * `[[02-Projects/SouthBendEventsScraperV2/_index]]`
   * Use the project tracking skill at [`.agents/skills/obsidian-project-vault/SKILL.md`](.agents/skills/obsidian-project-vault/SKILL.md) to maintain consistent documentation, wikilinks, and YAML frontmatter.

---

## 2. Step-by-Step Implementation Workflow

When asked to work on a component or step of the system:
1. **Consult Current Status:**
   * Review [docs/TASK_TRACKER.md](docs/TASK_TRACKER.md) to inspect granular task IDs, status checkboxes, and task history.
   * Read [docs/IMPLEMENTATION_LOG.md](docs/IMPLEMENTATION_LOG.md) to check overall component state and what decisions have been superseded.
2. **Review Relevant Section in Design Doc:** Locate the corresponding section in [docs/DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md).
3. **Plan & Confirm:** Formulate the implementation plan, ensuring no regression or deviation from performance benchmarks and requirements.
4. **Implement Clean, Tested Code:** Write robust, production-grade code with error handling, type hinting, and tests.
5. **Update Task & Implementation Logs:**
   * In [docs/TASK_TRACKER.md](docs/TASK_TRACKER.md), update task checkbox (`[ ]` -> `[/]` -> `[x]` -> `[-]`), increment the summary table, and add an entry under **Task History & Change Log**.
   * In [docs/IMPLEMENTATION_LOG.md](docs/IMPLEMENTATION_LOG.md), add a chronological entry and update the component status matrix.
   * If architectural specs changed or were superseded, update [docs/DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md) revision history and add an ADR in the implementation log.

---

## 3. Key Reference Locations

* **System Design & Specs:** [docs/DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md)
* **Granular Task Tracker & Change Log:** [docs/TASK_TRACKER.md](docs/TASK_TRACKER.md)
* **Implementation & Supersession History:** [docs/IMPLEMENTATION_LOG.md](docs/IMPLEMENTATION_LOG.md)
* **Project Tracking Skill:** [.agents/skills/obsidian-project-vault/SKILL.md](.agents/skills/obsidian-project-vault/SKILL.md)
