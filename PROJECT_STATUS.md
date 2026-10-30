# Trip Planner (LangGraph + FastAPI + Amazon Bedrock): Project Status

> Keep this file in the repo root. Update the status table after every phase.
> To resume in any new session, paste the "Resume prompt" at the bottom.

## 1. Project summary

| Item | Value |
|---|---|
| Goal | Learn LangGraph by building a trip planner: 2-3 cities, 5-day itinerary |
| Language / tooling | Python 3.12, **uv** (application project, `package = false`) |
| API layer | FastAPI |
| LLM provider | **Amazon Bedrock** via `langchain-aws` (`ChatBedrockConverse`, provider `bedrock_converse`) |
| Orchestration | LangChain (Phase 0), LangGraph (from Phase 1) |
| Storage (later) | PostgreSQL for checkpointer + Store, pgvector for RAG |
| Author background | 6 yrs full-stack (Java/Spring Boot, React, AWS), new to Python and AI agents |

## 2. Phase tracker

| Phase | Theme | Est. time | Status |
|---|---|---|---|
| 0 | Setup and foundations | 3-4 days | **DONE** |
| 1 | First graph (State, nodes, edges) | 1 week | TODO |
| 2 | Tools and routing (ReAct, conditional edges) | 1 week | TODO |
| 3 | Parallelism and loops (`Send`, reducers, validator loop) | 1 week | TODO |
| 4 | Persistence and human-in-the-loop (checkpointer, `interrupt`, time travel) | 1 week | TODO |
| 5 | Streaming, memory, subgraphs | 1 week | TODO |
| 6 | Guardrails and hardening | 4-5 days | TODO |
| 7 | Advanced: multi-agent, handoffs, agentic RAG, multimodal, evals, deploy | 1.5-2 weeks | TODO |

## 3. What Phase 0 covered

| Area | Done |
|---|---|
| Tooling | uv installed, project created, Python pinned, deps added with `uv add` |
| Project structure | `app/` with `api`, `core`, `schemas`, `tools`, `guardrails`, `rag`, `graph/{nodes,subgraphs,agents}`, plus `tests/`, `evals/` |
| Config | `.env` + `.env.example`, Pydantic `Settings` in `app/core/config.py` |
| AWS / Bedrock | Credentials, region, model ID or inference profile in `.env`; connectivity check with a scratch script |
| LangChain basics | `init_chat_model`, `ChatPromptTemplate`, chain with `\|`, `with_structured_output` |
| Schema | `TripRequest` Pydantic model (cities, days, budget, currency, interests, travelers, start_date, missing_info) |
| FastAPI basics | `GET /health`, `POST /parse-request`, Swagger UI at `/docs` |
| Git | `.gitignore` added (secrets, venv, caches, scratch files) |

**Phase 0 deliverable (working):** `POST /parse-request` turns free text into a typed `TripRequest`; vague input fills `missing_info` instead of inventing values.

### Lessons learned in Phase 0

| Problem | Cause | Fix |
|---|---|---|
| `Expected a Python module at src\trip_planner\__init__.py` | `[build-system]` in `pyproject.toml` made uv try to build the project as a package | Remove `[build-system]` and `[project.scripts]`, add `[tool.uv] package = false` |
| `No module named 'app'` | Missing `__init__.py` in `app/` | Add `__init__.py` to every package folder, run from project root |
| Python 3.14 in venv instead of 3.12 | Pin missing | `uv python pin 3.12`, then `uv sync` |
| Bedrock "on-demand throughput not supported" | Model needs an inference profile | Use the profile ID (`us.` / `eu.` / `apac.` prefix) from the console |

## 4. Current project structure

```
trip-planner/
├── app/
│   ├── main.py              # FastAPI app, /health, includes routers
│   ├── api/parse.py         # POST /parse-request
│   ├── core/config.py       # Settings (aws_region, llm_model_id, llm_temperature)
│   ├── schemas/trip.py      # TripRequest
│   ├── graph/nodes/intake.py  # prompt | model.with_structured_output(TripRequest)
│   ├── tools/  guardrails/  rag/  graph/subgraphs/  graph/agents/   # empty, filled in later phases
├── tests/   evals/
├── .env  .env.example  .gitignore
├── pyproject.toml  uv.lock  .python-version
└── PROJECT_STATUS.md
```

## 5. Run commands

| Task | Command |
|---|---|
| Install / sync deps | `uv sync` |
| Run API (dev) | `uv run fastapi dev app/main.py` or `uv run uvicorn app.main:app --reload` |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Add a dependency | `uv add <package>` |

## 6. Remaining phases in detail

| Phase | Build | Key concepts | Planned API additions | Done when... |
|---|---|---|---|---|
| **1** | `TripState`; nodes: Intake, City Allocator, Itinerary Builder; compile graph at startup (`lifespan`) | State, nodes, edges, `compile`, `invoke`, Mermaid diagram | `POST /trips` | A 3-node graph returns a basic itinerary |
| **2** | Tools: weather, places search, distance/travel time, currency; ReAct loop; "ask if info missing" routing | `@tool`, `ToolNode`, `tools_condition`, conditional edges | `GET /tools/weather` (debug) | Agent uses live tools and routes on missing info |
| **3** | Parallel city research; builder + validator loop with retry cap (max 3) | `Send`, reducers (`operator.add`), cycles, reflection | same API, richer output | Cities researched in parallel; validator loop works |
| **4** | Checkpointer (SQLite then Postgres); `interrupt` for missing info, hotel choice, final approval; edit and rewind | Checkpointer, threads, `interrupt`, `Command(resume=...)`, state history, time travel | `GET /trips/{id}`, `POST /trips/{id}/resume`, `GET /trips/{id}/history`, `POST /trips/{id}/rewind` | Pause, approve, edit, rewind a trip over HTTP |
| **5** | Streaming progress; long-term preferences; City Research as a subgraph | `astream` modes, SSE, Store, namespaces, subgraphs | `GET /trips/{id}/stream`, `GET/PUT /users/{id}/preferences` | Progress streams live; preferences persist across trips |
| **6** | Input / tool / output guardrails; retries, fallbacks, timeouts; request IDs, rate limiting. Compare with Bedrock Guardrails | Guardrail nodes, grounding check, safe failure | Global error handlers | Bad inputs rejected; every stop grounded in tool results |
| **7** | Supervisor + Flight/Hotel/Activities agents; Booking handoff; agentic RAG (retrieve, grade, rewrite); image input; evals; LangSmith tracing; auth; Docker; deploy on ECS | Supervisor, handoffs, `Command(graph=Command.PARENT)`, agentic RAG, multimodal, evals, deployment | `POST /trips/{id}/book`, `POST /trips/{id}/upload`, `GET /trips/{id}/export`, `POST /auth/login` | Team plans, RAG answers visa questions, evals pass, runs in Docker |

## 7. Coverage map

| Concept | Phase |
|---|---|
| Structured output | 0 |
| State, nodes, edges | 1 |
| Tools, ReAct, conditional edges | 2 |
| `Send`, reducers, validator loop | 3 |
| Checkpointer, threads, `interrupt`, time travel | 4 |
| Streaming, Store, subgraphs | 5 |
| Guardrails, error handling | 6 |
| Multi-agent, handoffs, agentic RAG, multimodal, evals, deployment | 7 |

## 8. Decisions and conventions

| Decision | Reason |
|---|---|
| Model ID lives in `.env` (`LLM_MODEL_ID`), not in code | Switch models with no code change |
| `llm_model_id` has no default in `Settings` | Fail fast at startup if missing |
| Compile the graph once at startup, reuse per request | Avoid rebuild cost on every call |
| Use `ChatBedrockConverse` (not `ChatBedrock`) | Best tool-calling and structured-output support |
| Cap every loop (max 3 retries) | Prevent runaway token cost |
| Scratch scripts named `scratch_*.py` | Git-ignored |
| Never commit `.env`; commit `.env.example` | Secrets safety |

## 9. Open items before Phase 1

| Item | Status |
|---|---|
| Set an AWS Budgets alert for Bedrock spend | Recommended |
| Make first commit (`git add . && git commit -m "phase 0: setup, parse-request"`) | To do |
| Optional: add a `TestClient` test for `/health` and `/parse-request` | Optional |
| Try 3 messy inputs (Hinglish, no budget, 4 cities in 2 days) | Optional |

## 10. Resume prompt (paste into a new session)

```
I'm building a LangGraph trip planner (2-3 cities, 5-day itinerary) with FastAPI,
uv, and Amazon Bedrock (ChatBedrockConverse). I'm a beginner in Python and AI
agents but have 6 years of software engineering experience (Java/Spring Boot,
React, AWS). I prefer step-by-step plans with tables, plain-English
explanations, and exam tips.

Phase 0 is complete: project structure, Settings, TripRequest schema, intake
chain with structured output, GET /health, POST /parse-request.
Project structure and decisions are in PROJECT_STATUS.md (pasted below).

Start Phase 1: install LangGraph, define TripState, build the 3-node graph
(Intake -> City Allocator -> Itinerary Builder), compile at startup, and expose
POST /trips.

[paste the contents of PROJECT_STATUS.md here]
```
