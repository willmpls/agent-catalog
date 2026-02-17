# Proto Event Contracts Agent

A self-contained OpenCode agent that reviews and evolves protobuf event/message schemas against a hybrid event contract standard, plus test fixtures and an eval harness to validate that it works.

## Install

Copy the agent file into your project:

```bash
mkdir -p .opencode/agents
cp agents/proto-event-contracts/agent.md <your-project>/.opencode/agents/proto-event-contracts.md
```

## Usage

### Review a proto schema

```bash
opencode run --agent proto-event-contracts -f path/to/your/event.proto -- "Review this proto"
```

The agent will:
1. Check for available tooling (`buf`, `api-linter`)
2. Run safe automation (format, lint, breaking checks)
3. Review the schema against the inlined event contract standard
4. Output a structured review with must-fix and should-fix findings

### Convert a non-proto schema to proto

The agent also handles Avro (`.avsc`) and JSON Schema (`.schema.json` / `.json`) inputs via its Section 2b workflow:

```bash
# Avro
opencode run --agent proto-event-contracts -f path/to/event.avsc -- "Convert this Avro schema to proto. We want Tier A hybrid semantics."

# JSON Schema
opencode run --agent proto-event-contracts -f path/to/event.schema.json -- "Convert this JSON Schema to proto. This is a delta-only producer today."
```

The agent will:
1. Normalize the source schema (identify keys, timestamps, enums, nullable/unions, maps, polymorphism)
2. Propose proto-first modeling following the event contract standard
3. Output a proto file + friction report for constructs that don't map cleanly

**Note**: There is no automated validation of Avro/JSON Schema files — the agent reads them as text and applies its conversion guide (Sections 2b and 8) to produce a proto conversion plan and output.

## Running Evals

### Prerequisites

- Python 3.10+
- `opencode` CLI installed and on PATH
- The agent file installed in the current project (see Install above)

### Run

```bash
python agents/proto-event-contracts/evals/run_evals.py
```

### Options

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Print full agent output for each case |
| `--model` / `-m` | Override the model (e.g., `--model sonnet`) |

### Interpreting Results

The eval runner uses **deterministic keyword grading**:

- **Clean fixtures** (`examples/good/`): fail if the agent output contains "must-fix" or "must fix"
- **Finding fixtures** (`examples/needs-review/`): pass if all expected keywords appear in the output and the correct severity level is mentioned

Exit code 0 means all cases passed; exit code 1 means at least one failed.

### Optional: LLM-as-Judge

For higher-fidelity grading (e.g., checking that the agent's reasoning is sound, not just that keywords appear), you can wrap the eval runner with an LLM judge. This is left as an exercise — the deterministic grading is sufficient for the well-defined fixtures included here.

## Non-Proto Input Examples

Example Avro and JSON Schema files for testing the agent's conversion workflow (Section 2b).

### Avro (`.avsc`)

| File | Description | Key Friction |
|------|-------------|--------------|
| `avro-input/customer_event.avsc` | CRM customer change event | Epoch millis timestamps, nullable unions for "what changed", money as `double`, `UPSERT`/`DELETE` enum |
| `avro-input/transaction_event.avsc` | Payment gateway event | Polymorphic union (card/bank/wallet), money as `double`, no change op (state machine) |
| `avro-input/inventory_snapshot.avsc` | Periodic WMS full dump | Not a change event (pure snapshot), denormalized computed field, nested arrays |
| `avro-input/order_lifecycle_event.avsc` | Complex OMS order event | 3-level nesting, 3 polymorphic fulfillment types, split payments, returns inside line items, 8 enums |
| `avro-input/mega_commerce_event.avsc` | Universal "everything nullable" schema | 6 entity types in one schema, 63 fields all nullable, JSON-in-string blobs, string enums — tests decomposition |

### JSON Schema (`.schema.json`)

| File | Description | Key Friction |
|------|-------------|--------------|
| `json-schema-input/user_event.schema.json` | Identity service user event | ISO-8601 timestamps, string enums, nested org memberships, `additionalProperties` map |
| `json-schema-input/iot_telemetry.schema.json` | High-frequency sensor telemetry | Not a CRUD entity (append-only), dynamic metric names, `number` type ambiguity (float vs int), nested location |
| `json-schema-input/notification_event.schema.json` | Polymorphic notification delivery | Channel-dependent detail objects (email/sms/push/webhook), delivery state machine, trigger provenance |

## Fixture Reference

| Fixture | Expected | Severity | Key Signals |
|---------|----------|----------|-------------|
| `good/tier_a_hybrid.proto` | Clean | — | Correct Tier A with `after` + `update_mask` (no `patch`); `Operation` enum with `OPERATION_*` prefix |
| `good/tier_b_delta_only.proto` | Clean | — | Correct Tier B with `patch` + `update_mask` + `sequence`; `Operation` enum with `OPERATION_*` prefix |
| `needs-review/missing_event_meta.proto` | Finding | must-fix | No EventMeta message or meta field |
| `needs-review/missing_update_mask.proto` | Finding | must-fix | Has after but no update_mask |
| `needs-review/no_protovalidate.proto` | Finding | should-fix | Zero protovalidate constraints |
| `needs-review/bad_enum.proto` | Finding | should-fix | No UNSPECIFIED=0, no defined_only, bare value names (no `OPERATION_*` prefix), legacy UPSERT instead of CREATE+UPDATE |
| `needs-review/delta_without_sequence.proto` | Finding | should-fix | Patch-only producer, no sequence (LWW limitations; prefer Tier A/CDC) |
| `needs-review/tier_a_with_redundant_patch.proto` | Finding | should-fix | Tier A schema with redundant `patch` field alongside `after` |
