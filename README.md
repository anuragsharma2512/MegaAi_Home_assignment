# Real-Time Multi-Agent LLM Orchestration and Evaluation System

This is a containerized FastAPI system that demonstrates dynamic multi-agent routing, auditable tool orchestration, context-budget enforcement, adversarial evaluation, prompt rewrite proposals, SSE streaming, and database-backed execution traces.

The default implementation is deterministic and local so it runs without API keys. It is structured so a real LLM adapter can be added behind the agent classes using environment-only configuration.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Log query UI: `http://localhost:8080`
- PostgreSQL: `localhost:5432`

## Exactly Five API Endpoints

`POST /query`

Submits a query and returns `text/event-stream`. Events include routing decisions, active agent, token chunks, tool/budget metadata, and completion payload.

```bash
curl -N -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Explain RAG citations with FastAPI streaming\"}"
```

`GET /trace/{job_id}`

Returns the ordered trace for a job, including agent decisions, hashes, latency, token counts, and policy violations.

`GET /eval/latest`

Returns the latest eval summary by category and dimension. If no eval exists, it runs the 15-case harness once.

`POST /prompt-rewrites/{rewrite_id}/decision`

Approves or rejects a pending rewrite.

```json
{"decision":"approved","reviewer":"ritik","reason":"Improves citation scoring prompt"}
```

`POST /eval/targeted`

Runs only previously failed cases using the latest approved prompts and stores a diff against the prior run.

All error responses use:

```json
{"error_code":"MACHINE_READABLE_CODE","message":"Human readable message","job_id":"optional-job-id"}
```

## Agents

The orchestrator is the only component that mediates handoffs. Agents communicate through `SharedContext`; they do not call each other directly.

- Decomposition agent: creates typed subtasks and dependency graphs.
- Retrieval agent: performs multi-hop retrieval over at least two chunks and records chunk-level citations.
- Validation agent: exercises real tool interfaces for database lookup, Python execution, and self-reflection.
- Critique agent: scores individual claims, flags exact spans, and avoids whole-output criticism.
- Synthesis agent: resolves critique findings and emits a final answer with sentence-level provenance.
- Compression agent: summarizes old conversational filler while preserving structured tool outputs, scores, and citations.
- Meta prompt agent: finds weak eval dimensions and proposes prompt rewrites for human review.

## Tools and Failure Contracts

The tool registry logs input, output, latency, acceptance, failure mode, and retry attempts. Each retry is stored separately.

- `web_search`: returns structured URLs and relevance scores. Failure modes: timeout, empty results, malformed input.
- `python_sandbox`: runs restricted Python snippets and returns stdout, stderr, exit code. Failure modes: timeout, malformed input, execution error.
- `data_lookup`: converts natural language to safe local SQL over seeded `knowledge_facts`. Failure modes: timeout, empty results, malformed input.
- `self_reflection`: rereads prior session outputs for contradictions. Failure modes: empty results, malformed input.

Fallback logic is explicit in `app/tools/registry.py`, not hidden in prompts.

## Evaluation

The harness includes 15 cases:

- 5 straightforward correctness cases.
- 5 ambiguous cases testing decomposition.
- 5 adversarial cases covering prompt injection, false premises, contradiction handling, timeouts, and unsafe code.

Scoring dimensions:

- Answer correctness.
- Citation accuracy.
- Contradiction resolution quality.
- Tool selection efficiency.
- Context budget compliance.
- Critique agreement with final output.

Every score has a numeric value and written justification. Eval results store prompts, tool calls, outputs, scores, timestamps, and job IDs.

## Self-Improving Prompt Loop

After an eval run, the meta agent can propose a rewrite for the prompt tied to the weakest failed dimension. The rewrite is stored with a structured diff and justification but is not applied automatically. A human must approve it through the prompt decision endpoint. Targeted re-eval then runs failed cases and stores performance deltas.

## Observability

Trace events use a consistent schema:

- timestamp
- agent ID
- event type
- input hash
- output hash
- latency
- token count
- policy violations
- payload

The log query service at `http://localhost:8080` can filter by `job_id`, `agent_id`, and `event_type`.

## Known Limitations

- The default “LLM” behavior is deterministic rule-based logic, not a hosted model. This makes the assessment runnable without credentials but limits natural language quality.
- The Python sandbox is process-isolated with restricted builtins, but it is not a hardened production sandbox.
- The worker service is present and initialized, while query streaming is handled synchronously by the API to preserve live SSE semantics.
- Database setup uses `create_all`; production deployments should use migrations.
- The web search tool is a structured stub, not live internet search.

## What I Would Build Next

- Add an LLM provider abstraction with OpenAI-compatible structured output validation.
- Move long-running query jobs to a durable queue while keeping SSE fan-out.
- Add Alembic migrations.
- Harden sandboxing with containers or a microVM runtime.
- Add auth, tenancy, rate limits, and PII-safe log redaction.

See [docs/architecture.md](docs/architecture.md) for the architecture diagram and [AI_ATTESTATION.md](AI_ATTESTATION.md) for AI collaboration disclosure.
