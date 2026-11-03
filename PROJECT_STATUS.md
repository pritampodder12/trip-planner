# Trip Planner (LangGraph + FastAPI + Amazon Bedrock): Project Status

> Keep this file in the repo root. Update the tracker after every phase.
> To resume in any new session, paste the "Resume prompt" at the bottom.
> **Last updated:** after Phase 2 (Phases 0, 1 and 2 complete, next is Phase 3).

## 1. Project summary

| Item | Value |
|---|---|
| Goal | Learn LangGraph by building a trip planner: 2-3 cities, 5-day itinerary |
| Language / tooling | Python 3.12, **uv** (application project, `package = false`) |
| API layer | FastAPI (graph compiled once in `lifespan`, stored in `app.state.graph`) |
| LLM provider | **Amazon Bedrock** via `langchain-aws` (`ChatBedrockConverse`, provider `bedrock_converse`) |
| Orchestration | LangChain for prompts, structured output and tools; LangGraph for the workflow |
| External data (no API keys) | Open-Meteo (geocoding, weather), MET Norway (weather fallback), Wikipedia search (places), Frankfurter/ECB (currency) |
| Storage (later) | PostgreSQL for checkpointer + Store, pgvector for RAG |
| Author background | 6 yrs full-stack (Java/Spring Boot, React, AWS), new to Python and AI agents |

## 2. Phase tracker

| Phase | Theme | Est. time | Status |
|---|---|---|---|
| 0 | Setup and foundations | 3-4 days | **DONE** |
| 1 | First graph (State, nodes, edges) | 1 week | **DONE** |
| 2 | Tools and routing (ReAct, conditional edges) | 1 week | **DONE** (happy flow verified; negative flow still to test) |
| 3 | Parallelism and loops (`Send`, reducers, validator loop) | 1 week | **NEXT** |
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
| AWS / Bedrock | Credentials, region, model ID or inference profile in `.env` |
| LangChain basics | `init_chat_model`, `ChatPromptTemplate`, chain with `\|`, `with_structured_output` |
| Schema | `TripRequest` (cities, days, budget, currency, interests, travelers, start_date, missing_info) |
| FastAPI basics | `GET /health`, `POST /parse-request`, Swagger UI at `/docs` |
| Git | `.gitignore` added (secrets, venv, caches, scratch files) |

### Phase 1: First graph (DONE)

| Area | Done |
|---|---|
| State | `TripState` (TypedDict, `total=False`) |
| Nodes | `intake_node`, `city_allocator_node`, `itinerary_builder_node` (each returns only the keys it changed) |
| Graph | Linear graph built in `app/graph/build.py`, compiled once in the FastAPI `lifespan` |
| Shared LLM | `app/core/llm.py` with cached `get_llm()` |
| Schemas | `TripIn`, `CityStay`, `CityPlan`, `DayPlan`, `Itinerary`, `TripResponse` in `app/schemas/plan.py` |
| API | `POST /trips` |

### Phase 2: Tools and routing (DONE)

| Area | Done |
|---|---|
| Tools (4) | `get_weather_forecast`, `search_places`, `estimate_travel`, `convert_currency` in `app/tools/`, collected in `ALL_TOOLS` |
| Tool design | `@tool` with docstring as description; type hints as argument schema; errors returned as readable strings, never raised |
| Shared HTTP helper | `geocode()` (cached) and `get_json()` (retry on timeouts, 429, 5xx) in `app/tools/geo.py`; descriptive `HEADERS` User-Agent with contact info |
| Weather resilience | Open-Meteo first, MET Norway fallback, `WEATHER_MOCK=true` switch for development (output clearly labelled `[MOCK DATA]`) |
| Required-field check in code | `validate_request_node` decides `missing_required` (cities, days, days_too_few) and non-blocking `assumptions` (budget, start date, interests); the LLM's `missing_info` is no longer used for decisions |
| Conditional edge #1 | `validate_request` routes to `ask_user` (returns `status: needs_input` with questions) or to planning |
| ReAct research loop | `prepare_research → research_agent ⇄ tools → save_notes`, using `bind_tools`, `ToolNode`, `tools_condition` |
| First reducer | `messages: Annotated[list[AnyMessage], add_messages]` in `TripState` |
| Grounded builder | Itinerary builder uses `research_notes` and is told to use only places named there |
| Loop safety | `recursion_limit=30` plus `GraphRecursionError` handling in `POST /trips` |
| API | `TripResponse` now has `status` (`needs_input` / `complete`), `questions`, `assumptions`, optional `city_plan` and `itinerary`; optional debug endpoint `GET /tools/weather` |

**Working deliverable:** free text goes in. Missing required info returns follow-up questions. Otherwise the agent researches with live tools and returns a grounded itinerary with assumptions listed. Happy flow tested with several unrelated prompts.

## 4. Current graph

```
START → intake → validate_request ──missing required info?──► ask_user → END
                       │ ok
                       ▼
                 city_allocator → prepare_research → research_agent ◄──┐
                                                          │            │
                                              tool calls? ├─ yes ► tools
                                                          │ no
                                                          ▼
                                                     save_notes → itinerary_builder → END
```

## 5. Current project structure

```
trip-planner/
├── app/
│   ├── main.py                 # FastAPI app + lifespan (compiles graph once), routers, /health
│   ├── api/
│   │   ├── parse.py            # POST /parse-request
│   │   ├── trips.py            # POST /trips (runs graph, recursion_limit, needs_input/complete)
│   │   └── tools.py            # GET /tools/weather (debug, optional)
│   ├── core/
│   │   ├── config.py           # Settings (aws_region, llm_model_id, llm_temperature, weather_mock)
│   │   └── llm.py              # get_llm() -> Bedrock chat model (cached)
│   ├── schemas/
│   │   ├── trip.py             # TripRequest
│   │   └── plan.py             # TripIn, CityStay, CityPlan, DayPlan, Itinerary, TripResponse
│   ├── tools/
│   │   ├── __init__.py         # ALL_TOOLS
│   │   ├── geo.py              # HEADERS, geocode(), get_json() with retry
│   │   ├── weather.py          # Open-Meteo -> MET Norway fallback, mock switch
│   │   ├── places.py           # Wikipedia search by city + interest
│   │   ├── travel.py           # haversine distance, rough road time
│   │   └── currency.py         # Frankfurter (ECB) conversion
│   ├── graph/
│   │   ├── state.py            # TripState (includes messages with add_messages)
│   │   ├── build.py            # nodes, edges, 2 conditional edges, cycle, compile
│   │   └── nodes/
│   │       ├── intake.py       # intake_node (+ parse_trip_request for /parse-request)
│   │       ├── validate.py     # validate_request_node, route_after_validation, ask_user_node
│   │       ├── allocator.py    # city_allocator_node
│   │       ├── research.py     # prepare_research_node, research_agent_node, save_notes_node
│   │       └── builder.py      # itinerary_builder_node (uses research_notes)
│   ├── guardrails/  rag/  graph/subgraphs/  graph/agents/   # empty, filled in later phases
├── tests/   evals/
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
| Inspect graph node by node | `uv run scratch_graph.py` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Add a dependency | `uv add <package>` |

## 7. Key concepts learned (one line each)

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
| `with_structured_output` | Forces the LLM to return data matching a Pydantic class |
| `prompt \| model` | A chain: output of one step feeds the next, always in a straight line |
| State (`TripState`) | The one shared object every node reads from and writes to |
| Node | A function that takes state and returns only the keys it changed |
| Edge | A fixed "run this next" wire between two nodes |
| `StateGraph` / `compile()` | Builder, then a frozen reusable runnable (`ainvoke`, `astream`) |
| Default overwrite | A returned key replaces the old value unless the field has a reducer |
| Reducer (`add_messages`) | Changes a field from "overwrite" to "append"; Phase 3 writes custom ones |
| `stream_mode="updates"` | Shows what each node returned, great for debugging |
| FastAPI `lifespan` / `app.state` | Startup hook and shared singleton holder (like `@PostConstruct` and a bean) |
| `@tool` | Turns a function into an LLM-callable tool; docstring = description, type hints = schema |
| Tool call | The LLM only **requests** a call; `ToolNode` actually runs it |
| `bind_tools` | Tells the LLM which tools exist |
| ReAct loop | A graph cycle: LLM → tools → LLM, exits when the LLM answers in plain text |
| Conditional edge | A router function returns the next node's name from the state |
| `tools_condition` | Built-in router: "tools" if the last message has tool calls, else END |
| `recursion_limit` | Cap on total graph steps; stops runaway loops |
| Decide in code, extract with the LLM | Required-field checks are deterministic Python, not LLM judgment |
| Tools return errors as text | The LLM can adapt; crashes end the request |
| Retry only temporary errors | Timeouts, 429 and 5xx; never 4xx |
| Fallback + mock | Every external dependency needs a plan B; mock data must be labelled |

## 8. Lessons learned (bugs and fixes)

| Problem | Cause | Fix |
|---|---|---|
| `Expected a Python module at src\trip_planner\__init__.py` | `[build-system]` in `pyproject.toml` made uv build the project as a package | Remove `[build-system]` and `[project.scripts]`, add `[tool.uv] package = false` |
| `No module named 'app'` | Missing `__init__.py` in `app/` | Add `__init__.py` to every package folder, run from project root |
| Python 3.14 in venv instead of 3.12 | Pin missing | `uv python pin 3.12`, then `uv sync` |
| Bedrock "on-demand throughput not supported" | Model needs an inference profile | Use the profile ID (`us.` / `apac.` prefix) from the console |
| `.env` got committed | `.gitignore` doesn't affect already-tracked files | `git rm --cached .env`, amend or recommit; rotate keys if any were pushed |
| Mermaid printed `<bound method ...>` | Missing `()` on `draw_mermaid` | `print(graph.get_graph().draw_mermaid())` |
| Node output showed `None`; later "Field required" | Typo in state key (`ininerary` vs `itinerary`); dict keys aren't checked at runtime | Keep names identical across state, node, schema and API; use editor rename (F2) |
| `'State' object has no attribute 'graph'` | `lifespan` not attached or stale server | `FastAPI(..., lifespan=lifespan)`, restart, check startup log |
| Weather tool: `503 Service Unavailable` | Open-Meteo forecast API outage (confirmed on its status page) | Retry helper, MET Norway fallback, `WEATHER_MOCK` switch |
| Places tool: `403 Please respect our robot policy` | Wikimedia needs a descriptive User-Agent with real contact info | Set `HEADERS` User-Agent with app name and your email or repo URL |
| Places returned nothing useful | Parameter typo `grsearch` instead of `gsrsearch`; APIs ignore unknown params silently | Compare the final URL with the docs character by character |
| Error message ended with literal `e` | f-string missing braces (`: e` instead of `: {e}`) | Use `{type(e).__name__}: {e}` so empty messages still show the class |

## 9. Known limitations of the current graph

| Limitation | Fixed in |
|---|---|
| The LLM can still ignore the research notes and invent places or numbers | Phase 6 (output grounding guardrail) |
| Places come from Wikipedia search, so quality is uneven | Phase 7 (better source or RAG) |
| Days may not add up exactly; budget is not checked | Phase 3 (validator loop) |
| Cities are researched one after another via a single agent (slow) | Phase 3 (`Send` for parallel research) |
| After `needs_input` the client must resend a full request; the graph forgets the first attempt | Phase 4 (checkpointer + `interrupt` / resume) |
| No streaming, so responses feel slow (several LLM calls and tool calls) | Phase 5 |
| No input guardrails (off-topic, prompt injection) | Phase 6 |
| Weather works only about 10 days ahead; later trips get no forecast | Accepted; notes should say so |
| Negative-flow tests not run yet (vague input, too few days, failing tools) | Open item below |

## 10. Remaining phases in detail

| Phase | Build | Key concepts | Planned API additions | Done when... |
|---|---|---|---|---|
| **3** | Parallel per-city research (each city its own research task); builder + validator loop (days add up, budget fits, every day has places) with retry cap (max 3); custom reducers for merging parallel results | `Send` (map-reduce), reducers (`operator.add` and custom), cycles, reflection pattern | same API, richer output (warnings, validation report) | Cities researched in parallel; validator loop corrects a bad itinerary and stops at the cap |
| **4** | Checkpointer (SQLite then Postgres); `interrupt` for missing info, hotel choice, final approval; edit and rewind | Checkpointer, threads, `interrupt`, `Command(resume=...)`, state history, time travel | `GET /trips/{id}`, `POST /trips/{id}/resume`, `GET /trips/{id}/history`, `POST /trips/{id}/rewind` | Pause, approve, edit, rewind a trip over HTTP |
| **5** | Streaming progress; long-term preferences; City Research as a subgraph | `astream` modes, SSE, Store, namespaces, subgraphs | `GET /trips/{id}/stream`, `GET/PUT /users/{id}/preferences` | Progress streams live; preferences persist across trips |
| **6** | Input / tool / output guardrails; retries, fallbacks, timeouts; request IDs, rate limiting. Compare with Bedrock Guardrails | Guardrail nodes, grounding check, safe failure | Global error handlers | Bad inputs rejected; every stop grounded in tool results |
| **7** | Supervisor + Flight/Hotel/Activities agents; Booking handoff; agentic RAG (retrieve, grade, rewrite); image input; evals; LangSmith tracing; auth; Docker; deploy on ECS | Supervisor, handoffs, `Command(graph=Command.PARENT)`, agentic RAG, multimodal, evals, deployment | `POST /trips/{id}/book`, `POST /trips/{id}/upload`, `GET /trips/{id}/export`, `POST /auth/login` | Team plans, RAG answers visa questions, evals pass, runs in Docker |

## 11. Coverage map

| Concept | Phase | Status |
|---|---|---|
| Structured output | 0 | Done |
| State, nodes, edges, compile | 1 | Done |
| Tools, ReAct, conditional edges, `add_messages` | 2 | Done |
| `Send`, custom reducers, validator loop | 3 | Next |
| Checkpointer, threads, `interrupt`, time travel | 4 | Todo |
| Streaming, Store, subgraphs | 5 | Todo |
| Guardrails, error handling | 6 | Todo |
| Multi-agent, handoffs, agentic RAG, multimodal, evals, deployment | 7 | Todo |

## 12. Decisions and conventions

| Decision | Reason |
|---|---|
| Model ID lives in `.env` (`LLM_MODEL_ID`), not in code | Switch models with no code change |
| `llm_model_id` has no default in `Settings` | Fail fast at startup if missing |
| One shared `get_llm()` in `app/core/llm.py` | Single place to change model settings |
| Compile the graph once in `lifespan`, reuse per request | Avoid rebuild cost on every call |
| Nodes return only changed keys as a dict | LangGraph merges partial updates into state |
| Required-field validation in plain Python | Free, instant and consistent; the LLM only extracts |
| Tools return errors as text, never raise | The LLM can adapt and the request survives |
| Tool HTTP calls go through `get_json()` with retry | Absorbs temporary 429/5xx/timeouts |
| Weather has a fallback and a labelled mock | A single free API outage must not block development |
| Builder may only use places from `research_notes` | Reduces invented places (full enforcement in Phase 6) |
| Cap every loop (recursion limit, max tool calls, retries) | Prevent runaway token cost |
| Scratch scripts named `scratch_*.py` | Git-ignored |
| Never commit `.env`; commit `.env.example` | Secrets safety |
| Prefer `AWS_PROFILE` (SSO) over access keys | No secret to leak; ECS task role replaces keys in Phase 7 |

## 13. Open items before Phase 3

| Item | Status |
|---|---|
| Negative-flow tests: `plan me a trip` (expect `needs_input`), 3 cities in 2 days (expect "too few days"), unknown city, a failing tool | Deferred by choice; do before Phase 6 at the latest |
| Set `WEATHER_MOCK=false` once real weather works; confirm `.env.example` lists `WEATHER_MOCK` | To check |
| Confirm the User-Agent in `geo.py` has your real contact (Wikimedia and MET Norway require it) | To check |
| Confirm `.env` is untracked (`git ls-files .env` prints nothing), then commit (`git commit -m "phase 2: tools, ReAct loop, conditional edges"`) | To do |
| Set an AWS Budgets alert for Bedrock spend (the research loop makes many LLM calls) | Recommended |
| Optional: add `TestClient` tests (use `with TestClient(app)` so lifespan runs) and mock the weather tool | Optional |

## 14. Resume prompt (paste into a new session)

```
I'm building a LangGraph trip planner (2-3 cities, 5-day itinerary) with FastAPI,
uv, and Amazon Bedrock (ChatBedrockConverse). I'm a beginner in Python and AI
agents but have 6 years of software engineering experience (Java/Spring Boot,
React, AWS). I prefer step-by-step plans with tables, plain-English
explanations, and exam tips.

Phases 0, 1 and 2 are complete: project setup, Settings, structured output,
TripState with messages, validate_request (required fields checked in code) with
a conditional edge to ask_user, city_allocator, a ReAct research loop with four
tools (weather with fallback and mock switch, places, travel estimate,
currency), grounded itinerary_builder, POST /trips returning status
needs_input or complete. Structure, concepts, lessons and decisions are in
PROJECT_STATUS.md (pasted below).

Start Phase 3: run city research in parallel with Send (map-reduce) using
custom reducers, and add a validator loop after the builder (days add up,
budget fits, each day has real places) with a retry cap of 3 and a final
"best attempt with warnings" fallback. Keep the existing API shape and add
validation warnings to the response.

[paste the contents of PROJECT_STATUS.md here]
```