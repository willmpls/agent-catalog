# Agent Catalog

A collection of self-contained [OpenCode](https://opencode.ai) agents — each with its own definition, docs, examples, and evals.

## Available Agents

| Agent | Description |
|-------|-------------|
| [proto-event-contracts](agents/proto-event-contracts/) | Reviews and evolves protobuf event/message schemas against a hybrid event contract standard |

## Install an Agent

Copy the agent's definition file into your project's `.opencode/agents/` directory:

```bash
mkdir -p .opencode/agents
cp agents/<agent-name>/agent.md <your-project>/.opencode/agents/<agent-name>.md
```

Then run it:

```bash
opencode run --agent <agent-name> -f <input-file> -- "<prompt>"
```

See each agent's README for detailed usage and examples.

## Adding a New Agent

### 1. Create the directory

```
agents/<agent-name>/
├── agent.md              # Agent definition (source of truth)
├── README.md             # Agent-specific docs, usage, examples
├── examples/             # Input fixtures and example files
│   ├── good/             # Known-good examples (agent should approve these)
│   └── needs-review/     # Known-bad examples (agent should flag issues)
└── evals/                # Evaluation harness
    ├── cases.json        # Test case definitions
    └── run_evals.py      # Eval runner script
```

### 2. Write `agent.md`

This is the agent definition that OpenCode loads at runtime. It uses YAML frontmatter for configuration followed by the agent's system prompt in Markdown.

```markdown
---
description: One-line summary of what the agent does.
mode: primary
temperature: 0.2
steps: 40

permission:
  edit: allow
  webfetch: deny
  bash:
    "*": deny
    # Allowlist specific commands the agent needs
    "command -v *": allow
    "ls*": allow
---

# Agent Name

You are an agent that does X. All normative knowledge is inlined below.

## 1. Preflight

...

## 2. Workflow

...
```

**Frontmatter fields:**

| Field | Purpose |
|-------|---------|
| `description` | Shown in `opencode agents list` and used for agent selection |
| `mode` | `primary` (takes over the session) or `support` (runs alongside) |
| `temperature` | LLM sampling temperature — lower is more deterministic |
| `steps` | Max agentic steps before the agent stops |
| `permission` | Tool-level allowlists — keep bash locked down to only what the agent needs |

**Tips:**
- Inline all domain knowledge directly in the Markdown body. The agent should be self-contained — no external reference files needed at runtime.
- Use `permission.bash` allowlists to restrict shell access to only the commands the agent actually needs (linters, formatters, read-only git, etc.).
- Keep the prompt focused: one agent, one domain. If you need coverage across multiple domains, create separate agents.

### 3. Write `README.md`

The agent README should cover:

- **What the agent does** — a paragraph explaining the domain and approach
- **Install** — how to copy `agent.md` into a target project
- **Usage** — example `opencode run` commands for each workflow the agent supports
- **Running evals** — how to run the eval harness and interpret results
- **Fixture reference** — table of example files with expected outcomes and key signals

See [`agents/proto-event-contracts/README.md`](agents/proto-event-contracts/README.md) for a complete example.

### 4. Add examples

Place input fixtures under `examples/`. Organize by outcome:

- `examples/good/` — files the agent should approve with no findings
- `examples/needs-review/` — files with known issues the agent should catch

Add subdirectories for other input types as needed (e.g., `examples/avro-input/`, `examples/json-schema-input/`).

### 5. Add evals

**`evals/cases.json`** — array of test cases, each referencing a fixture path relative to the agent directory:

```json
[
  {
    "fixture": "examples/good/clean_example.xyz",
    "expect_clean": true,
    "severity": null,
    "keywords": []
  },
  {
    "fixture": "examples/needs-review/bad_example.xyz",
    "expect_clean": false,
    "severity": "must-fix",
    "keywords": ["expected_keyword", "another_keyword"]
  }
]
```

**`evals/run_evals.py`** — script that runs the agent against each fixture and grades the output. See [`agents/proto-event-contracts/evals/run_evals.py`](agents/proto-event-contracts/evals/run_evals.py) for a reusable starting point. The key pattern:

- Resolve fixture paths relative to the agent directory (`script_dir.parent`)
- Invoke `opencode run --agent <agent-name> -f <fixture>` via subprocess
- Grade with deterministic keyword matching (check for expected severity + keywords in output)

### 6. Symlink for local development

To test the agent locally without copying files:

```bash
ln -s ../../agents/<agent-name>/agent.md .opencode/agents/<agent-name>.md
```

### 7. Update this README

Add a row to the [Available Agents](#available-agents) table:

```markdown
| [your-agent](agents/your-agent/) | What your agent does |
```
