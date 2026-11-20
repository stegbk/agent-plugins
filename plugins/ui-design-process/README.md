# ui-design-process

A repeatable way to design an app's UI with agents. A workflow script catalogues what the product does, writes the
user journeys, has three designer personas (The Minimalist, The Apple Fan, The Gestalt Functionalist) propose
complete designs as HTML mockups, has them and an art director critique each other, audits every design for
reachability, ranks them with a judge panel, fuses the best into one design, and builds a tabbed studio page that
the owner reviews on a phone. The skill explains when to run it, every argument, how the owner reviews and approves,
and the lessons from earlier runs.

A run starts roughly 60 to 90 agents and takes one to two hours; the skill says so before starting.

## Permissions
| Permission | Why |
|---|---|
| Workflow | run `skills/ui-design-process/workflow-template.js` |
| Agent | the workflow's designer, critic, auditor and judge agents |
| Read | the project's code, specs and docs (the inventory) |
| Write | all output goes to the scratch folder given as `scr`; the agents never edit, commit or push the repository |
| Artifact | publish the studio page for the owner |
| WebFetch, WebSearch | the agents may look up design references on the web |

Network: web references chosen by the agents. The studio page itself loads nothing from other sites (no web
fonts, scripts or stylesheets). The agents read the project and may consult the web, then write files, so the
store records an injection review for each version. No hooks, no MCP servers.

## Configuration
None. The project paths (`scr`, `readers`, `base`) are given as workflow arguments each time the skill is used.

## Harnesses
Claude Code only (the Workflow tool).

## Tests
`uv run pytest plugins/ui-design-process/tests -q` from the store repo checks that the skill documents every
workflow argument and that the template declares its phases.
