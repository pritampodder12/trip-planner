# Trip Planner (LangGraph + FastAPI + Amazon Bedrock): Project Status

> Keep this file in the repo root. Update the tracker after every phase.
> To resume in any new session, paste the "Resume prompt" at the bottom.
> **Last updated:** after Phase 1 (Phases 0 and 1 complete, next is Phase 2).

## 1. Project summary

| Item | Value |
|---|---|
| Goal | Learn LangGraph by building a trip planner: 2-3 cities, 5-day itinerary |
| Language / tooling | Python 3.12, **uv** (application project, `package = false`) |
| API layer | FastAPI (graph compiled once in `lifespan`, stored in `app.state.graph`) |
| LLM provider | **Amazon Bedrock** via `langchain-aws` (`ChatBedrockConverse`, provider `bedrock_converse`) |
| Orchestration | LangChain for prompts and structured output, LangGraph for the workflow |
| Storage (later) | PostgreSQL for checkpointer + Store, pgvector for RAG |
| Author background | 6 yrs full-stack (Java/Spring Boot, React, AWS), new to Python and AI agents |

## 2. Phase tracker

| Phase | Theme | Est. time | Status |
|---|---|---|---|
| 0 | Setup and foundations | 3-4 days | **DONE** |
| 1 | First graph (State, nodes, edges) | 1 week | **DONE** |
| 2 | Tools and routing (ReAct, conditional edges) | 1 week | **NEXT** |
| 3 | Parallelism and loops (`Send`, reducers, validator loop) | 1 week | TODO |
| 4 | Persistence and human-in-the-loop (checkpointer, `interrupt`, time travel) | 1 week | TODO |
| 5 | Streaming, memory, subgraphs | 1 week | TODO |
| 6 | Guardrails and hardening | 4-5 days | TODO |
| 7 | Advanced: multi-agent, handoffs, agentic RAG, multimodal, evals, deploy | 1.5-2 weeks | TODO |

## 3. What is built so far

### Phase 0: Setup and foundations (DONE)

| Area | Done |
|---|---|
| Tooling | uv installed, project created, Python pinned, deps added with `uv add` |
| Project structure | `app/` with `api`, `core`, `schemas`, `tools`, `guardrails`, `rag`, `graph/{nodes,subgraphs,agents}`, plus `tests/`, `evals/` |
| Config | `.env` + `.env.example`, Pydantic `Settings` in `app/core/config.py` |
| AWS / Bedrock | Credentials, region, model ID or inference profile in `.env`; connectivity checked with a scratch script |
| LangChain basics | `init_chat_model`, `ChatPromptTemplate`, chain with `\|`, `with_structured_output` |
| Schema | `TripRequest` (cities, days, budget, currency, interests, travelers, start_date, missing_info) |
| FastAPI basics | `GET /health`, `POST /parse-request`, Swagger UI at `/docs` |
| Git | `.gitignore` added (secrets, venv, caches, scratch files) |

### Phase 1: First graph (DONE)

| Area | Done |
|---|---|
| LangGraph installed | `uv add langgraph` |
| Shared LLM helper | `app/core/llm.py` with cached `get_llm()` |
| State | `TripState` (TypedDict, `total=False`): `user_text`, `request`, `city_plan`, `itinerary` |
| Nodes | `intake_node`, `city_allocator_node`, `itinerary_builder_node` (each returns only the keys it changed) |
| Graph | `START → intake → city_allocator → itinerary_builder → END`, built in `app/graph/build.py` |
| New schemas | `TripIn`, `CityStay`, `CityPlan`, `DayPlan`, `Itinerary`, `TripResponse` in `app/schemas/plan.py` |
| API | `POST /trips` returns `request`, `city_plan` and `itinerary` |
| Debugging aid | `scratch_graph.py` (git-ignored) prints the Mermaid diagram and per-node updates with `stream_mode="updates"` |

**Working deliverable:** free text goes in, and a parsed request, a city/day split and a day-by-day itinerary come back as JSON.

## 4. Current project structure

```
trip-planner/
├── app/
│   ├── main.py                 # FastAPI app + lifespan (compiles graph once), routers, /health
│   ├── api/
│   │   ├── parse.py            # POST /parse-request
│   │   └── trips.py            # POST /trips (runs the graph)
│   ├── core/
│   │   ├── config.py           # Settings (aws_region, llm_model_id, llm_temperature)
│   │   └── llm.py              # get_llm() -> Bedrock chat model (cached)
│   ├── schemas/
│   │   ├── trip.py             # TripRequest
│   │   └── plan.py             # TripIn, CityStay, CityPlan, DayPlan, Itinerary, TripResponse
│   ├── graph/
│   │   ├── state.py            # TripState
│   │   ├── build.py            # build_graph(): nodes, edges, compile
│   │   └── nodes/
│   │       ├── intake.py       # intake_node (+ parse_trip_request used by /parse-request)
│   │       ├── allocator.py    # city_allocator_node
│   │       └── builder.py      # itinerary_builder_node
│   ├── tools/  guardrails/  rag/  graph/subgraphs/  graph/agents/   # empty, filled in later phases
├── tests/   evals/
├── scratch_graph.py            # local debugging only (git-ignored)
├── .env  .env.example  .gitignore
├── pyproject.toml  uv.lock  .python-version
└── PROJECT_STATUS.md
```

## 5. Run commands

| Task | Command |
|---|---|
| Install / sync deps | `uv sync` |
| Run API (dev) | `uv run uvicorn app.main:app --reload` (or `uv run fastapi dev app/main.py`) |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| Inspect graph node by node | `uv run scratch_graph.py` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Add a dependency | `uv add <package>` |

## 6. Key concepts learned (one line each)

| Concept | Note |
|---|---|
| uv | One tool for Python versions, venv and dependencies (like npm + nvm in one) |
| `package = false` | Tells uv this is an app, not a library to build |
| `__init__.py` | Marks a folder as an importable package |
| Pydantic `BaseModel` | A typed DTO that validates data and describes its shape to the LLM |
| `Field(description=...)` | That text is sent to the LLM as instructions, so write it carefully |
| `Settings` (pydantic-settings) | Typed access to `.env`; no default means it fails fast at startup |
| `init_chat_model` | Creates a chat model from provider and model ID, so switching models needs no code change |
| `ChatBedrockConverse` | Bedrock chat class with the best tool-calling and structured-output support |
| Inference profile | Region-prefixed model ID (`us.` / `apac.`) that some Bedrock models require |
| `ChatPromptTemplate` | A prompt with `{placeholders}` filled at call time |
| `with_structured_output` | Forces the LLM to return data matching a Pydantic class |
| `prompt \| model` | A chain: output of one step feeds the next, always in a straight line |
| State (`TripState`) | The one shared object every node reads from and writes to |
| Node | An async function that takes state and returns only the keys it changed |
| Edge | A fixed "run this next" wire between two nodes |
| `StateGraph` | The builder where you register nodes and edges |
| `compile()` | Freezes the graph into a reusable runnable (`ainvoke`, `astream`) |
| Default overwrite | A returned key replaces the old value (merging reducers come in Phase 3) |
| `stream_mode="updates"` | Shows what each node returned, great for debugging |
| FastAPI `lifespan` | Startup/shutdown hook; compile the graph once and keep it in `app.state` |
| `app.state` | Shared holder for singletons across requests, like a Spring bean |
| `uv run X` | Runs X inside the project's environment, no manual venv activation |

## 7. Lessons learned (bugs and fixes)

| Problem | Cause | Fix |
|---|---|---|
| `Expected a Python module at src\trip_planner\__init__.py` | `[build-system]` in `pyproject.toml` made uv build the project as a package | Remove `[build-system]` and `[project.scripts]`, add `[tool.uv] package = false` |
| `No module named 'app'` | Missing `__init__.py` in `app/` | Add `__init__.py` to every package folder, run from project root |
| Python 3.14 in venv instead of 3.12 | Pin missing | `uv python pin 3.12`, then `uv sync` |
| Bedrock "on-demand throughput not supported" | Model needs an inference profile | Use the profile ID (`us.` / `apac.` prefix) from the console |
| `.env` got committed | `.gitignore` doesn't affect already-tracked files | `git rm --cached .env`, amend or recommit; rotate keys if any were pushed |
| Mermaid printed `<bound method ...>` | Missing `()` on `draw_mermaid` | `print(graph.get_graph().draw_mermaid())` |
| Third node's output showed `None` | Typo in returned key (`ininerary` vs `itinerary`); state dict keys aren't checked at runtime | Keep names identical across state, node, schema and API; use editor rename (F2) |
| `'State' object has no attribute 'graph'` | `lifespan` not attached or stale server | `FastAPI(..., lifespan=lifespan)`, restart, check startup log |
| Pydantic "Field required" on `TripResponse` | Same typo in the schema field | Search the codebase for the misspelling and fix everywhere |

## 8. Known limitations of the current graph

| Limitation | Fixed in |
|---|---|
| Places, timings and prices come from LLM memory and may be wrong | Phase 2 (tools), Phase 6 (grounding guardrail) |
| No routing: input like "plan me a trip" still runs all three nodes | Phase 2 (conditional edges) |
| `missing_info` relies on the LLM (e.g. `start_date` may not be listed) | Phase 2 (compute missing fields in code) |
| Does not check that days add up or that budget fits | Phase 3 (validator loop) |
| No pause, approve or edit | Phase 4 |
| Three sequential LLM calls, so responses are slow | Phase 5 (streaming), Phase 3 (parallelism) |

## 9. Remaining phases in detail

| Phase | Build | Key concepts | Planned API additions | Done when... |
|---|---|---|---|---|
| **2** | Tools: weather, places search, distance/travel time, currency; ReAct loop; "ask if info missing" routing; required-field check in code | `@tool`, `ToolNode`, `tools_condition`, conditional edges | `GET /tools/weather` (debug) | Agent uses live tools and routes on missing info |
| **3** | Parallel city research; builder + validator loop with retry cap (max 3) | `Send`, reducers (`operator.add`), cycles, reflection | same API, richer output | Cities researched in parallel; validator loop works |
| **4** | Checkpointer (SQLite then Postgres); `interrupt` for missing info, hotel choice, final approval; edit and rewind | Checkpointer, threads, `interrupt`, `Command(resume=...)`, state history, time travel | `GET /trips/{id}`, `POST /trips/{id}/resume`, `GET /trips/{id}/history`, `POST /trips/{id}/rewind` | Pause, approve, edit, rewind a trip over HTTP |
| **5** | Streaming progress; long-term preferences; City Research as a subgraph | `astream` modes, SSE, Store, namespaces, subgraphs | `GET /trips/{id}/stream`, `GET/PUT /users/{id}/preferences` | Progress streams live; preferences persist across trips |
| **6** | Input / tool / output guardrails; retries, fallbacks, timeouts; request IDs, rate limiting. Compare with Bedrock Guardrails | Guardrail nodes, grounding check, safe failure | Global error handlers | Bad inputs rejected; every stop grounded in tool results |
| **7** | Supervisor + Flight/Hotel/Activities agents; Booking handoff; agentic RAG (retrieve, grade, rewrite); image input; evals; LangSmith tracing; auth; Docker; deploy on ECS | Supervisor, handoffs, `Command(graph=Command.PARENT)`, agentic RAG, multimodal, evals, deployment | `POST /trips/{id}/book`, `POST /trips/{id}/upload`, `GET /trips/{id}/export`, `POST /auth/login` | Team plans, RAG answers visa questions, evals pass, runs in Docker |

## 10. Coverage map

| Concept | Phase | Status |
|---|---|---|
| Structured output | 0 | Done |
| State, nodes, edges, compile | 1 | Done |
| Tools, ReAct, conditional edges | 2 | Next |
| `Send`, reducers, validator loop | 3 | Todo |
| Checkpointer, threads, `interrupt`, time travel | 4 | Todo |
| Streaming, Store, subgraphs | 5 | Todo |
| Guardrails, error handling | 6 | Todo |
| Multi-agent, handoffs, agentic RAG, multimodal, evals, deployment | 7 | Todo |

## 11. Decisions and conventions

| Decision | Reason |
|---|---|
| Model ID lives in `.env` (`LLM_MODEL_ID`), not in code | Switch models with no code change |
| `llm_model_id` has no default in `Settings` | Fail fast at startup if missing |
| One shared `get_llm()` in `app/core/llm.py` | Single place to change model settings |
| Compile the graph once in `lifespan`, reuse per request | Avoid rebuild cost on every call |
| Nodes return only changed keys as a dict | LangGraph merges partial updates into state |
| Use `ChatBedrockConverse` (not `ChatBedrock`) | Best tool-calling and structured-output support |
| Cap every loop (max 3 retries) | Prevent runaway token cost |
| Scratch scripts named `scratch_*.py` | Git-ignored |
| Never commit `.env`; commit `.env.example` | Secrets safety |
| Prefer `AWS_PROFILE` (SSO) over access keys | No secret to leak; ECS task role replaces keys in Phase 7 |

## 12. Open items before Phase 2

| Item | Status |
|---|---|
| Remove temporary `print("Graph compiled")` from `main.py` | To do |
| Confirm `.env` is untracked (`git ls-files .env` prints nothing) | To do |
| Commit Phase 1 (`git commit -m "phase 1: first 3-node graph"`) | To do |
| Set an AWS Budgets alert for Bedrock spend | Recommended |
| Optional: add a `TestClient` test (use `with TestClient(app)` so lifespan runs) | Optional |

## 13. Resume prompt (paste into a new session)

```
I'm building a LangGraph trip planner (2-3 cities, 5-day itinerary) with FastAPI,
uv, and Amazon Bedrock (ChatBedrockConverse). I'm a beginner in Python and AI
agents but have 6 years of software engineering experience (Java/Spring Boot,
React, AWS). I prefer step-by-step plans with tables, plain-English
explanations, and exam tips.

Phases 0 and 1 are complete: project setup, Settings, TripRequest schema,
shared get_llm(), TripState, a 3-node graph (intake -> city_allocator ->
itinerary_builder), compiled once in FastAPI lifespan, POST /trips working.
Structure, concepts, lessons and decisions are in PROJECT_STATUS.md (pasted below).

Start Phase 2: add tools (weather, places search, distance/travel time,
currency), a ReAct loop with ToolNode, and conditional edges so the graph asks
for missing info instead of planning a trip with no cities. Compute required
missing fields in code instead of trusting the LLM.

[paste the contents of PROJECT_STATUS.md here]
```