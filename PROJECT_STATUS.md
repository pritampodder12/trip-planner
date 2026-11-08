# Trip Planner (LangGraph + FastAPI + LLM): Project Status

> Keep this file in the repo root. Update the tracker after every phase.
> To resume in any new session, paste the "Resume prompt" at the bottom.
> **Last updated:** after Phase 3 (Phases 0 to 3 complete, next is Phase 4).

## 1. Project summary

| Item | Value |
|---|---|
| Goal | Learn LangGraph by building a trip planner: 2-3 cities, 5-day itinerary |
| Language / tooling | Python (3.12 pinned; check `uv run python --version`, earlier tracebacks showed 3.14), **uv** (application project, `package = false`) |
| API layer | FastAPI (graph compiled once in `lifespan`, stored in `app.state.graph`) |
| LLM provider (current) | **Azure OpenAI, `gpt-5-mini`**, via `langchain-openai` `ChatOpenAI(base_url=..., api_key=...)`; `reasoning_effort` lowered for speed |
| LLM provider (earlier) | Amazon Bedrock (`ChatBedrockConverse`, Nova, about 15 s per `/trips` call); switched because Bedrock was throwing errors. Can be revisited later |
| Orchestration | LangChain for prompts, structured output and tools; LangGraph for the workflow |
| External data (no API keys) | Open-Meteo (geocoding, weather), MET Norway (weather fallback), Wikipedia search (places), Frankfurter/ECB (currency) |
| Storage (later) | PostgreSQL for checkpointer + Store, pgvector for RAG |
| Author background | 6 yrs full-stack (Java/Spring Boot, React, AWS), new to Python and AI agents |

## 2. Phase tracker

| Phase | Theme | Est. time | Status |
|---|---|---|---|
| 0 | Setup and foundations | 3-4 days | **DONE** |
| 1 | First graph (State, nodes, edges) | 1 week | **DONE** |
| 2 | Tools and routing (ReAct, conditional edges) | 1 week | **DONE** (negative flow still to test) |
| 3 | Parallelism and loops (`Send`, reducers, validator loop) | 1 week | **DONE** |
| 4 | Persistence and human-in-the-loop (checkpointer, `interrupt`, time travel) | 1 week | **NEXT** |
| 5 | Streaming, memory, subgraphs | 1 week | TODO |
| 6 | Guardrails and hardening | 4-5 days | TODO |
| 7 | Advanced: multi-agent, handoffs, agentic RAG, multimodal, evals, deploy | 1.5-2 weeks | TODO |

## 3. What is built so far

### Phase 0: Setup and foundations (DONE)

| Area | Done |
|---|---|
| Tooling | uv installed, project created, deps added with `uv add` |
| Project structure | `app/` with `api`, `core`, `schemas`, `tools`, `guardrails`, `rag`, `graph/{nodes,subgraphs,agents}`, plus `tests/`, `evals/` |
| Config | `.env` + `.env.example`, Pydantic `Settings` in `app/core/config.py` |
| LangChain basics | `init_chat_model` / chat model factory, `ChatPromptTemplate`, chain with `\|`, `with_structured_output` |
| Schema | `TripRequest` (cities, days, budget, currency, interests, travelers, start_date, missing_info) |
| FastAPI basics | `GET /health`, `POST /parse-request`, Swagger UI at `/docs` |
| Git | `.gitignore` added (secrets, venv, caches, scratch files) |

### Phase 1: First graph (DONE)

| Area | Done |
|---|---|
| State | `TripState` (TypedDict, `total=False`) |
| Nodes | Each node returns only the keys it changed |
| Graph | Built in `app/graph/build.py`, compiled once in the FastAPI `lifespan` |
| Shared LLM | `app/core/llm.py` with cached `get_llm()` |
| API | `POST /trips` |

### Phase 2: Tools and routing (DONE)

| Area | Done |
|---|---|
| Tools | `get_weather_forecast`, `search_places`, `estimate_travel`, `convert_currency` in `app/tools/`, collected in `ALL_TOOLS` |
| Tool design | `@tool` with docstring as description; errors returned as readable strings, never raised |
| HTTP helper | `geocode()` (cached) and `get_json()` (retry on timeouts, 429, 5xx) in `app/tools/geo.py`; descriptive User-Agent with contact info |
| Weather resilience | Open-Meteo first, MET Norway fallback, `WEATHER_MOCK=true` switch (output labelled `[MOCK DATA]`) |
| Validation in code | `validate_request_node` decides `missing_required` and non-blocking `assumptions`; conditional edge to `ask_user` returns `status: needs_input` |
| ReAct loop | LLM ⇄ `ToolNode` with `tools_condition` (now lives inside the per-city mini-graph) |
| Loop safety | `recursion_limit=30` plus `GraphRecursionError` handling in `POST /trips` |

### Phase 3: Parallelism and loops (DONE)

| Area | Done |
|---|---|
| Parallel research | `fan_out_research` returns one `Send("research_city", {...})` per city; all cities researched concurrently |
| Per-city mini-graph | `app/graph/subgraphs/city_research.py`: agent ⇄ tools loop with weather, places and travel-estimate tools; prompt asks the LLM to request all independent tool calls in one step |
| Custom reducer | `city_notes: Annotated[dict[str, CityNotes], merge_dicts]`; each branch writes `{city: note}` and the reducer merges them (keyed by city so order doesn't matter) |
| Grounded shortlist | `research_city_node` parses place names out of `search_places` tool results in code (`places` list per city) |
| Fan-in | `research_city → itinerary_builder` edge; builder runs once after all cities finish |
| Allocator fix in code | `city_allocator_node` forces stay days to add up to the requested total |
| Builder with feedback | Takes per-city notes (in plan order) and, on retries, the previous itinerary plus the list of problems to fix; increments `attempts` |
| Cost field | `DayPlan.estimated_cost` (all travelers, trip currency); the trip total is computed in code, not by the LLM |
| Validator loop | `review_itinerary_node` (plain Python, zero tokens) checks day count and numbering, city order and days per city, empty slots, budget (5% tolerance); grounding mismatches are warnings only |
| Retry cap | `MAX_ATTEMPTS = 3`; `route_after_review` loops back to the builder or goes to `finalize`; `finalize_node` turns unresolved errors into warnings ("best attempt with warnings") |
| API | `TripResponse` adds `warnings` and `attempts` |
| Tests | `tests/test_review.py` (4 unit tests, no LLM); `pythonpath = ["."]` added to `[tool.pytest.ini_options]` |
| Timing aid | `scratch_graph.py` prints elapsed time per node update |

**Working deliverable:** missing info returns follow-up questions. Otherwise all cities are researched in parallel, an itinerary is built, checked by code, retried up to 3 times with feedback, and returned with `assumptions`, `warnings` and `attempts`.

### LLM provider switch and latency work (done between Phases 2 and 3)

| Topic | Note |
|---|---|
| Why switched | Bedrock was throwing errors; moved to Azure OpenAI `gpt-5-mini` |
| Symptom | `/trips` took over a minute vs about 15 s with Nova |
| Cause | `gpt-5-mini` is a reasoning model; it thinks before each of the many sequential LLM calls (default effort is medium) |
| Temperature | Does not help: GPT-5 reasoning models only accept temperature 1, and `langchain-openai` silently drops the value for `gpt-5*` models; it never affected speed |
| Main lever | `reasoning_effort` (`minimal` / `low` / `medium` / `high`; `none` is not available on gpt-5-mini); use `minimal` or `low` for extraction and routing, higher only if quality needs it |
| Do not cap max tokens tightly | Reasoning tokens count against the cap and can truncate answers |
| Phase 3 effect | Parallel city research and "all tool calls in one step" cut sequential round trips |
| Token logging | Option A: wrap `graph.ainvoke` in `get_usage_metadata_callback()` in `app/api/trips.py`, log `cb.usage_metadata` (needs `logging.basicConfig(level=logging.INFO)` in `main.py`). `output_token_details.reasoning` shows hidden thinking tokens. Pass `config=config` into nested `ainvoke` calls so callbacks see them. Option B (per-node handler) is available if wanted |

## 4. Current graph

```
START → intake → validate_request ──missing required info?──► ask_user → END
                       │ ok
                       ▼
                 city_allocator ──Send──► research_city (one per city, in parallel)
                                                │   (each runs the agent ⇄ tools mini-graph)
                                                ▼  fan-in: waits for all cities
                                  ┌──► itinerary_builder
                                  │            │
                                  │            ▼
                                  │     review_itinerary (plain Python)
                                  │            │
                                  └─ errors and attempts < 3        no errors, or cap reached
                                                            └──────► finalize → END
```

## 5. Current project structure

```
trip-planner/
├── app/
│   ├── main.py                 # FastAPI app + lifespan (compiles graph once), routers, /health
│   ├── api/
│   │   ├── parse.py            # POST /parse-request
│   │   ├── trips.py            # POST /trips (recursion_limit, needs_input/complete, optional token logging)
│   │   └── tools.py            # GET /tools/weather (debug, optional)
│   ├── core/
│   │   ├── config.py           # Settings (llm settings, azure_openai_*, weather_mock, ...)
│   │   └── llm.py              # LLM factory (Azure OpenAI gpt-5-mini via ChatOpenAI; reasoning_effort)
│   ├── schemas/
│   │   ├── trip.py             # TripRequest
│   │   └── plan.py             # TripIn, CityStay, CityPlan, DayPlan (estimated_cost), Itinerary, TripResponse (warnings, attempts)
│   ├── tools/
│   │   ├── __init__.py         # ALL_TOOLS
│   │   ├── geo.py              # HEADERS, geocode(), get_json() with retry
│   │   ├── weather.py          # Open-Meteo -> MET Norway fallback, mock switch
│   │   ├── places.py           # Wikipedia search by city + interest
│   │   ├── travel.py           # haversine distance, rough road time
│   │   └── currency.py         # Frankfurter (ECB) conversion (not used by the graph right now)
│   ├── graph/
│   │   ├── state.py            # TripState, CityNotes, merge_dicts reducer
│   │   ├── build.py            # nodes, edges, conditional edges, Send fan-out, validator loop, compile
│   │   ├── subgraphs/
│   │   │   └── city_research.py   # per-city ReAct mini-graph (agent ⇄ tools)
│   │   └── nodes/
│   │       ├── intake.py       # intake_node (+ parse_trip_request for /parse-request)
│   │       ├── validate.py     # validate_request_node, route_after_validation, ask_user_node
│   │       ├── allocator.py    # city_allocator_node (days normalised in code)
│   │       ├── research.py     # fan_out_research, research_city_node
│   │       ├── builder.py      # itinerary_builder_node (per-city notes + feedback)
│   │       └── review.py       # review_itinerary_node, route_after_review, finalize_node, MAX_ATTEMPTS
│   ├── guardrails/  rag/  graph/agents/   # empty, filled in later phases
├── tests/
│   └── test_review.py          # unit tests for the reviewer and the retry cap
├── evals/
├── scratch_tools.py  scratch_graph.py   # local debugging only (git-ignored)
├── .env  .env.example  .gitignore
├── pyproject.toml  uv.lock  .python-version
└── PROJECT_STATUS.md
```

## 6. Run commands

| Task | Command |
|---|---|
| Install / sync deps | `uv sync` |
| Run API (dev) | `uv run uvicorn app.main:app --reload` (or `uv run fastapi dev app/main.py`) |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| Test tools alone | `uv run scratch_tools.py` |
| Inspect graph node by node, with timings | `uv run scratch_graph.py` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Add a dependency | `uv add <package>` |

## 7. Key concepts learned (one line each)

| Concept | Note |
|---|---|
| uv, `package = false` | One tool for Python, venv and deps; app (not library) projects need no build system |
| Pydantic `BaseModel`, `Field(description=...)` | Typed DTO that validates data; the description is sent to the LLM as instructions |
| `Settings` (pydantic-settings) | Typed access to `.env`; no default means fail fast at startup |
| `with_structured_output` | Forces the LLM to return data matching a Pydantic class |
| `prompt \| model` | A chain: a straight line; LangGraph adds branches, loops and parallelism |
| State, node, edge, `compile()` | Shared object; function returning changed keys; fixed wire; frozen reusable runnable |
| Default overwrite vs reducer | A returned key replaces the old value unless the field has a reducer (`add_messages`, `merge_dicts`) |
| `stream_mode="updates"` | Shows what each node returned; add timestamps to find slow nodes |
| FastAPI `lifespan` / `app.state` | Startup hook and shared singleton holder |
| `@tool`, tool call, `bind_tools` | Docstring = description; the LLM only **requests** calls, `ToolNode` runs them |
| ReAct loop | A graph cycle: LLM → tools → LLM, exits when the LLM answers in plain text |
| Conditional edge, router function | A function reads state and returns the next node's name |
| `Send` (map-reduce) | Fan out one node run per item, each with a private payload |
| Custom reducer | Merges concurrent writes to one key; key by identity (city) so order and re-runs don't matter |
| Fan-in | A node after parallel branches runs once, after all finish |
| Validator loop (reflection) | Check output, feed errors back, retry; always with a cap |
| Errors vs warnings | Retry only on problems a retry can plausibly fix; report the rest |
| Decide in code, extract with the LLM | Required fields, day sums, budget totals and review checks are deterministic Python |
| Pass `config` to nested runs | Keeps callbacks (token usage, tracing) visible inside sub-invocations |
| `recursion_limit`, tool-call cap, `MAX_ATTEMPTS` | The three loop exits |
| Tools return errors as text; retry only temporary errors | Timeouts, 429 and 5xx; never 4xx |
| Fallback + labelled mock | Every external dependency needs a plan B |
| Reasoning models | Hidden thinking tokens drive latency; control with `reasoning_effort`, not temperature |
| Unit-test pure nodes | The reviewer needs no LLM, so tests are fast and free |

## 8. Lessons learned (bugs and fixes)

| Problem | Cause | Fix |
|---|---|---|
| `Expected a Python module at src\trip_planner\__init__.py` | `[build-system]` made uv build the project as a package | Remove `[build-system]` and `[project.scripts]`, add `[tool.uv] package = false` |
| `No module named 'app'` | Missing `__init__.py` in `app/` | Add `__init__.py` to every package folder, run from project root |
| Python 3.14 instead of 3.12 | Pin missing | `uv python pin 3.12`, then `uv sync` |
| Bedrock "on-demand throughput not supported" | Model needs an inference profile | Use the profile ID (`us.` / `apac.` prefix) |
| `.env` got committed | `.gitignore` doesn't affect tracked files | `git rm --cached .env`, amend or recommit; rotate keys if pushed |
| Mermaid printed `<bound method ...>` | Missing `()` | `print(graph.get_graph().draw_mermaid())` |
| Node output `None`; "Field required" | State key typo (`ininerary`) | Keep names identical across state, node, schema and API; use editor rename (F2) |
| `'State' object has no attribute 'graph'` | `lifespan` not attached or stale server | `FastAPI(..., lifespan=lifespan)`, restart, check startup log |
| Weather `503 Service Unavailable` | Open-Meteo outage | Retry helper, MET Norway fallback, `WEATHER_MOCK` switch |
| Places `403 Please respect our robot policy` | Wikimedia needs a User-Agent with real contact info | Set `HEADERS` with app name and your email or repo URL |
| Places returned nothing | Parameter typo `grsearch` for `gsrsearch`; APIs ignore unknown params | Compare the final URL with the docs |
| Error text ended with literal `e` | f-string missing braces | `{type(e).__name__}: {e}` |
| gpt-5-mini takes over a minute | Reasoning model thinks before every call; temperature is ignored | Lower `reasoning_effort`; parallelise and batch tool calls |
| `AttributeError: 'list' object has no attribute 'city'` | Used the list name (`stays`) instead of the loop item (`stay`) | `for i, stay in enumerate(stays)` and read `stay.city` |
| `ValueError: No messages found in input state` | Node returned `{"message": ...}` instead of `{"messages": ...}` | Use the plural key; `ToolNode`, `tools_condition` and `add_messages` all expect `messages` |

Recurring pattern: **misspelled keys and variable names fail late and far from the cause.** Search for the name after every state change and read the dict printed in the error.

## 9. Known limitations of the current graph

| Limitation | Fixed in |
|---|---|
| After `needs_input` the client must resend the full request; the graph forgets the first attempt | Phase 4 (checkpointer + `interrupt` / resume) |
| No way to pause, approve, edit or rewind | Phase 4 |
| No streaming; long waits feel slow | Phase 5 |
| City mini-graph is invoked from inside a node, not registered as a true subgraph | Phase 5 |
| Grounding is only a warning; the LLM can still invent details | Phase 6 (output guardrail) |
| No input guardrails (off-topic, prompt injection) | Phase 6 |
| Costs are LLM estimates, not real prices | Accepted; budget check is a sanity check |
| "Best attempt" is the last attempt, not the one with fewest errors | Optional improvement |
| Places come from Wikipedia search, so quality is uneven | Phase 7 (better source or RAG) |
| `convert_currency` tool exists but is not used by the graph | Phase 6 or 7 |
| Weather only about 10 days ahead | Accepted; notes should say so |
| Negative-flow tests not run yet | Open item below |

## 10. Remaining phases in detail

| Phase | Build | Key concepts | Planned API additions | Done when... |
|---|---|---|---|---|
| **4** | Checkpointer (async SQLite, then Postgres) compiled into the graph in `lifespan`; `thread_id` per trip; `ask_user` becomes a real `interrupt` for missing info; `interrupt` for final approval (approve or send edit feedback back to the builder); history and rewind | Checkpointer, threads, `interrupt`, `Command(resume=...)`, state history, time travel | `GET /trips/{id}`, `POST /trips/{id}/resume`, `GET /trips/{id}/history`, `POST /trips/{id}/rewind` | Pause, answer questions, approve or edit, and rewind a trip over HTTP without resending the original text |
| **5** | Streaming progress; long-term preferences; City Research as a real subgraph | `astream` modes, SSE, Store, namespaces, subgraphs | `GET /trips/{id}/stream`, `GET/PUT /users/{id}/preferences` | Progress streams live; preferences persist across trips |
| **6** | Input / tool / output guardrails; retries, fallbacks, timeouts; token budget guardrail; request IDs, rate limiting. Compare with provider-native guardrails | Guardrail nodes, grounding check, safe failure | Global error handlers | Bad inputs rejected; every stop grounded in tool results |
| **7** | Supervisor + Flight/Hotel/Activities agents; Booking handoff; agentic RAG (retrieve, grade, rewrite); image input; evals; LangSmith tracing; auth; Docker; deploy | Supervisor, handoffs, `Command(graph=Command.PARENT)`, agentic RAG, multimodal, evals, deployment | `POST /trips/{id}/book`, `POST /trips/{id}/upload`, `GET /trips/{id}/export`, `POST /auth/login` | Team plans, RAG answers visa questions, evals pass, runs in Docker |

## 11. Coverage map

| Concept | Phase | Status |
|---|---|---|
| Structured output | 0 | Done |
| State, nodes, edges, compile | 1 | Done |
| Tools, ReAct, conditional edges, `add_messages` | 2 | Done |
| `Send`, custom reducers, validator loop, retry cap | 3 | Done |
| Checkpointer, threads, `interrupt`, time travel | 4 | Next |
| Streaming, Store, subgraphs | 5 | Todo |
| Guardrails, error handling | 6 | Todo |
| Multi-agent, handoffs, agentic RAG, multimodal, evals, deployment | 7 | Todo |

## 12. Decisions and conventions

| Decision | Reason |
|---|---|
| Model and provider settings live in `.env`, not in code | Switch models with no code change |
| One shared LLM factory in `app/core/llm.py` | Single place to change model, reasoning effort and provider |
| Do not rely on `temperature` with gpt-5 models | Silently dropped; use `reasoning_effort` |
| Compile the graph once in `lifespan`, reuse per request | Avoid rebuild cost on every call |
| Nodes return only changed keys as a dict | LangGraph merges partial updates into state |
| Required-field validation, day sums, budget totals and review checks in plain Python | Free, instant, consistent and unit-testable |
| Parallel results stored in a dict keyed by city with a merge reducer | Order independence and no duplicates on re-run |
| Grounding mismatch is a warning, not an error | Minor name differences should not burn a retry |
| `MAX_ATTEMPTS = 3`, final answer is best attempt plus warnings | Bounded cost, always returns something useful |
| Pass `config` into nested `ainvoke` calls | Callbacks and tracing see the nested LLM calls |
| Tools return errors as text, never raise; HTTP goes through `get_json()` with retry | The LLM can adapt and the request survives |
| Weather has a fallback and a labelled mock | A single free API outage must not block development |
| Scratch scripts named `scratch_*.py` | Git-ignored |
| Never commit `.env`; commit `.env.example` | Secrets safety |

## 13. Open items before Phase 4

| Item | Status |
|---|---|
| Negative-flow tests: `plan me a trip` (expect `needs_input`), 3 cities in 2 days (expect "too few days"), unknown city, failing tool, very low budget (expect retries, then warnings after 3 attempts) | Deferred by choice; the low-budget case is the best test of the new loop |
| Confirm `uv run pytest` passes (4 reviewer tests) | To check |
| Confirm token logging is in `trips.py` (optional) and note `reasoning` tokens per call | Optional |
| Confirm `WEATHER_MOCK=false` and the User-Agent contact info in `geo.py` | To check |
| Update `.env.example` with the Azure OpenAI variable names (empty values) | To do |
| Confirm Python version (`uv run python --version`) and pin 3.12 if you prefer | Optional |
| Confirm `.env` is untracked (`git ls-files .env` prints nothing), then commit (`git commit -m "phase 3: parallel research, validator loop"`) | To do |

## 14. Resume prompt (paste into a new session)

```
I'm building a LangGraph trip planner (2-3 cities, 5-day itinerary) with FastAPI,
uv, and Azure OpenAI gpt-5-mini (previously Amazon Bedrock; I use ChatOpenAI
with a base_url and reasoning_effort). I'm a beginner in Python and AI agents
but have 6 years of software engineering experience (Java/Spring Boot, React,
AWS). I prefer step-by-step plans with tables, plain-English explanations, and
exam tips.

Phases 0 to 3 are complete: structured intake, validate_request with a
conditional edge to ask_user, city_allocator, parallel per-city research using
Send with a merge_dicts reducer and a per-city ReAct mini-graph, a builder with
feedback, a plain-Python reviewer with a retry loop capped at 3 attempts, and
POST /trips returning status needs_input or complete with assumptions,
warnings and attempts. Structure, concepts, lessons and decisions are in
PROJECT_STATUS.md (pasted below).

Start Phase 4: add a checkpointer (async SQLite first, Postgres later) compiled
into the graph in the FastAPI lifespan, use a thread_id per trip, turn ask_user
into a real interrupt so the user answers and the SAME run resumes (no full
resubmit), add an interrupt for final approval (approve, or send edit feedback
back to the builder), and add endpoints for status, resume, history and rewind
(time travel). Explain how Send, reducers and the retry loop behave with
checkpoints.

[paste the contents of PROJECT_STATUS.md here]
```