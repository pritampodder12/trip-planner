# Trip Planner (LangGraph + FastAPI + LLM): Project Status

> Keep this file in the repo root. Update the tracker after every phase.
> To resume in any new session, paste the "Resume prompt" at the bottom.
> **Last updated:** after Phase 4 (Phases 0 to 4 built; next is Phase 5).
> Section 7 is the step-by-step guide for testing the `/trips` endpoints.

## 1. Project summary

| Item | Value |
|---|---|
| Goal | Learn LangGraph by building a trip planner: 2-3 cities, 5-day itinerary |
| Language / tooling | Python (3.12 pinned; earlier tracebacks showed 3.14, so check `uv run python --version`), **uv** (application project, `package = false`) |
| API layer | FastAPI (graph compiled once in `lifespan` with a SQLite checkpointer, stored in `app.state.graph`) |
| LLM provider (current) | **Azure OpenAI, `gpt-5-mini`**, via `langchain-openai` `ChatOpenAI(base_url=..., api_key=...)`; `reasoning_effort` lowered for speed |
| LLM provider (earlier) | Amazon Bedrock (`ChatBedrockConverse`, Nova, about 15 s per call); switched because Bedrock was throwing errors |
| Orchestration | LangChain for prompts, structured output and tools; LangGraph for the workflow, persistence and human-in-the-loop |
| Persistence | `AsyncSqliteSaver` at `data/checkpoints.db` (git-ignored); Postgres planned for Phase 7 |
| External data (no API keys) | Open-Meteo (geocoding, weather), MET Norway (weather fallback), Wikipedia search (places), Frankfurter/ECB (currency) |
| Observability | Python logging (`app/core/logging_config.py`), `@log_call` decorator, per-request token usage summary |
| Author background | 6 yrs full-stack (Java/Spring Boot, React, AWS), new to Python and AI agents |

## 2. Phase tracker

| Phase | Theme | Est. time | Status |
|---|---|---|---|
| 0 | Setup and foundations | 3-4 days | **DONE** |
| 1 | First graph (State, nodes, edges) | 1 week | **DONE** |
| 2 | Tools and routing (ReAct, conditional edges) | 1 week | **DONE** |
| 3 | Parallelism and loops (`Send`, reducers, validator loop) | 1 week | **DONE** |
| 4 | Persistence and human-in-the-loop (checkpointer, `interrupt`, resume, time travel) | 1 week | **DONE** (confirm the HTTP walkthrough in section 7 and the open items in section 14) |
| 5 | Streaming, memory, subgraphs | 1 week | **NEXT** |
| 6 | Guardrails and hardening | 4-5 days | TODO |
| 7 | Advanced: multi-agent, handoffs, agentic RAG, multimodal, evals, deploy | 1.5-2 weeks | TODO |

## 3. What is built so far

### Phase 0: Setup and foundations (DONE)

| Area | Done |
|---|---|
| Tooling | uv installed, project created, deps added with `uv add` |
| Structure | `app/` with `api`, `core`, `schemas`, `tools`, `guardrails`, `rag`, `graph/{nodes,subgraphs,agents}`, plus `tests/`, `evals/` |
| Config | `.env` + `.env.example`, Pydantic `Settings` in `app/core/config.py` |
| LangChain basics | Chat model factory, `ChatPromptTemplate`, chain with `\|`, `with_structured_output` |
| Schema | `TripRequest` (cities, days, budget, currency, interests, travelers, start_date, missing_info) |
| FastAPI basics | `GET /health`, `POST /parse-request`, Swagger UI at `/docs` |
| Git | `.gitignore` (secrets, venv, caches, scratch files, local DBs) |

### Phase 1: First graph (DONE)

State (`TripState`, TypedDict), nodes returning only changed keys, graph built in `app/graph/build.py`, shared LLM factory in `app/core/llm.py`.

### Phase 2: Tools and routing (DONE)

| Area | Done |
|---|---|
| Tools | `get_weather_forecast`, `search_places`, `estimate_travel`, `convert_currency` in `app/tools/`; docstring = description; errors returned as text |
| HTTP helper | `geocode()` (cached) and `get_json()` (retry on timeouts, 429, 5xx); User-Agent with real contact info |
| Weather resilience | Open-Meteo, then MET Norway fallback, plus `WEATHER_MOCK=true` switch (labelled `[MOCK DATA]`) |
| Validation in code | `validate_request_node` decides `missing_required` and non-blocking `assumptions` |
| ReAct loop | LLM ⇄ `ToolNode` with `tools_condition` (now inside the per-city mini-graph) |

### Phase 3: Parallelism and loops (DONE)

| Area | Done |
|---|---|
| Parallel research | `fan_out_research` returns one `Send("research_city", ...)` per city |
| Per-city mini-graph | `app/graph/subgraphs/city_research.py`: agent ⇄ tools, tool calls batched in one step |
| Custom reducer | `city_notes` with `merge_dicts`, keyed by city |
| Validator loop | Plain-Python `review_itinerary_node` (day count, city order, empty slots, budget); `MAX_ATTEMPTS = 3`; `finalize_node` turns unresolved errors into warnings |
| Code over LLM | Day sums, budget totals, review checks are deterministic Python; `estimated_cost` per day, total computed in code |
| Tests | `tests/test_review.py` |

### Phase 4: Persistence and human-in-the-loop (DONE)

| Area | Done |
|---|---|
| Checkpointer | `AsyncSqliteSaver` opened with `async with` in the FastAPI `lifespan`; graph compiled with it (`build_graph(checkpointer)`); DB at `data/checkpoints.db` |
| Threads | One `thread_id` (uuid4 hex) per trip; all state saved after every step |
| Clarification pause | `ask_user_node` calls `interrupt({"type": "questions", ...})`; the answer is appended to `user_text` and the graph loops back to `intake`; capped at `MAX_CLARIFY_ROUNDS = 3`, then ends as `incomplete` |
| Approval pause | New `human_review_node` (`nodes/approval.py`) calls `interrupt({"type": "approval", ...})`; approve ends the run, edit feedback goes back to the builder; capped at `MAX_REVISIONS = 3` |
| Endpoints | `POST /trips`, `GET /trips/{id}`, `POST /trips/{id}/resume`, `GET /trips/{id}/history`, `POST /trips/{id}/rewind` |
| Time travel | Rewind replays from a checkpoint (`ainvoke(None, config_with_checkpoint_id)`), creating a fork; LLM nodes after it run again |
| Status model | `needs_input`, `awaiting_approval`, `complete`, `incomplete` |
| Logging | `setup_logging()`; `@log_call("node" / "tool")` decorator (logs called / finished / paused / failed with timings); explicit info logs in routers and endpoints |
| Token logging | `_summarize_usage()` plus `get_usage_metadata_callback()` in `trips.py`; one line per HTTP call with total, input, output, reasoning and cached tokens |
| Tests | `tests/test_routing.py` for the two new routers |
| Scratch aids | `scratch_interrupt.py` (pause/resume demo with `InMemorySaver`), `scratch_graph.py` (per-node timings) |

### LLM provider switch and latency notes

| Topic | Note |
|---|---|
| Cause of slowness | `gpt-5-mini` is a reasoning model; it thinks before each call |
| Temperature | Ignored for GPT-5 reasoning models (`langchain-openai` drops it); never affected speed |
| Main lever | `reasoning_effort` (`minimal` / `low` / `medium` / `high`; `none` not available on gpt-5-mini) |
| Don't cap max tokens tightly | Reasoning tokens count against the cap |
| Measure it | Token log line shows `reasoning` tokens; compare with `output` |

## 4. Current graph

```
START → intake → validate_request ─┬─ complete ──────────► city_allocator ──Send──► research_city (parallel, one per city)
            ▲                      ├─ missing, round < 3 ► ask_user  ⏸ interrupt(questions)      │ fan-in
            └──────────────────────┘   (answer appended to user_text)                            ▼
                                   └─ missing, round = 3 ► END (status "incomplete")     ┌──► itinerary_builder
                                                                                         │          ▼
                                                                                         │   review_itinerary (plain Python)
                                                                                         │          │
                                                                          errors, attempts < 3 ─────┘          no errors / cap reached
                                                                                                                      ▼
                                                                                                                  finalize
                                                                                                                      ▼
                                                                                                         human_review  ⏸ interrupt(approval)
                                                                                                    edit (revisions < 3) │      │ approved / cap
                                                                                         itinerary_builder ◄─────────────┘      ▼
                                                                                                                              END
```

## 5. Current project structure

```
trip-planner/
├── app/
│   ├── main.py                 # logging setup, lifespan (AsyncSqliteSaver + compile graph), routers, /health
│   ├── api/
│   │   ├── parse.py            # POST /parse-request
│   │   ├── trips.py            # start, status, resume, history, rewind; token usage logging
│   │   └── tools.py            # GET /tools/weather (debug, optional)
│   ├── core/
│   │   ├── config.py           # Settings (llm, azure_openai_*, weather_mock, checkpoint_db, log_level)
│   │   ├── llm.py              # LLM factory (Azure OpenAI gpt-5-mini; reasoning_effort)
│   │   └── logging_config.py   # setup_logging(), log_call decorator
│   ├── schemas/
│   │   ├── trip.py             # TripRequest
│   │   └── plan.py             # TripIn, CityStay, CityPlan, DayPlan, Itinerary, TripResponse, ResumeIn, RewindIn, CheckpointOut
│   ├── tools/                  # __init__ (ALL_TOOLS), geo, weather, places, travel, currency
│   ├── graph/
│   │   ├── state.py            # TripState (+ clarify_rounds, revisions, approved), CityNotes, merge_dicts
│   │   ├── build.py            # build_graph(checkpointer=None)
│   │   ├── subgraphs/city_research.py
│   │   └── nodes/              # intake, validate (ask_user interrupt), allocator, research, builder, review, approval
│   ├── guardrails/  rag/  graph/agents/   # empty, filled in later phases
├── data/checkpoints.db         # created at runtime, git-ignored
├── tests/                      # test_review.py, test_routing.py
├── evals/
├── scratch_tools.py  scratch_graph.py  scratch_interrupt.py   # local debugging only (git-ignored)
├── .env  .env.example  .gitignore
├── pyproject.toml  uv.lock  .python-version
└── PROJECT_STATUS.md
```

## 6. Run commands

| Task | Command |
|---|---|
| Install / sync deps | `uv sync` |
| Run API (dev) | `uv run uvicorn app.main:app --reload` |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| Test tools alone | `uv run scratch_tools.py` |
| Graph node by node, with timings | `uv run scratch_graph.py` |
| Pause/resume demo without HTTP | `uv run scratch_interrupt.py` |
| Unit tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Find `@log_call` written without parentheses | `Get-ChildItem app -Recurse -Filter *.py \| Select-String '@log_call\s*$'` |
| More detailed logs | set `LOG_LEVEL=DEBUG` in `.env` |

## 7. How to test the `/trips` endpoints, step by step

### 7.1 Before you start

| # | Check |
|---|---|
| 1 | `.env` has the LLM settings; `WEATHER_MOCK=true` is fine for offline testing, `false` for real weather |
| 2 | Start the server from the project root: `uv run uvicorn app.main:app --reload` |
| 3 | The terminal shows `Graph compiled with SQLite checkpointer` and `Application startup complete` |
| 4 | Keep the terminal visible: the logs are your best debugging tool (they show each node, router decision and token total) |
| 5 | Open `http://127.0.0.1:8000/docs`. Calls to `/trips` can take 30-90 seconds, so wait for the response |

**Two ways to call the API:** Swagger UI (click an endpoint, "Try it out", paste the body, "Execute"), or PowerShell. PowerShell setup, once per window:

```powershell
$base = "http://127.0.0.1:8000"
function Call($method, $path, $body = $null) {
    $args = @{ Method = $method; Uri = "$base$path"; TimeoutSec = 300 }
    if ($body) { $args.ContentType = "application/json"; $args.Body = $body }
    Invoke-RestMethod @args
}
```

Use `... | ConvertTo-Json -Depth 10` to print a response in full.

### 7.2 Status meanings

| `status` | Meaning | Next call |
|---|---|---|
| `needs_input` | Required info is missing; see `questions` | `resume` with `answer` |
| `awaiting_approval` | Itinerary is ready; see `itinerary`, `warnings`, `estimated_total` | `resume` with `approved` (and `feedback` if false) |
| `complete` | Approved (or revision cap reached) | None |
| `incomplete` | Still missing info after 3 clarification rounds | Start a new trip |

Note: a **successful run now ends at `awaiting_approval`**, not `complete`. The trip only completes after you approve.

### 7.3 Tests, in order

| # | Test | Request | Expected response | Expected logs |
|---|---|---|---|---|
| 1 | Health | `GET /health` | `{"status":"ok"}` | none |
| 2 | **Happy path to approval** | `POST /trips` `{"text":"5 days in Jaipur and Udaipur, 40000 INR, 2 people, love food and forts"}` | `status: awaiting_approval`, `thread_id`, `city_plan`, `itinerary` (5 days), `estimated_total`, `assumptions` (for example no start date), `attempts: 1` | `node intake_node`, `Validation: ... missing_required=[]`, 2 parallel `research_city_node`, `tool ... called with {...}`, `Router: ...`, `node human_review_node paused`, token usage line |
| 3 | Save the `thread_id` | PowerShell: `$id = $r.thread_id` | | |
| 4 | **Status** | `GET /trips/{thread_id}` | Same data as test 2 | `GET /trips/...` |
| 5 | **Request an edit** | `POST /trips/{thread_id}/resume` `{"approved": false, "feedback": "Make day 2 more relaxed"}` | `awaiting_approval` again, `revisions: 1`, itinerary changed | `User asked for changes (revision 1)`, builder runs again, paused again |
| 6 | **Approve** | `POST /trips/{thread_id}/resume` `{"approved": true}` | `status: complete`, `approved: true` | `Itinerary approved by the user` |
| 7 | **History** | `GET /trips/{thread_id}/history` | List of checkpoints, newest first, each with `checkpoint_id`, `step`, `next` | `GET .../history` |
| 8 | **Rewind** | Pick a checkpoint whose `next` is `["itinerary_builder"]`, then `POST /trips/{thread_id}/rewind` `{"checkpoint_id": "<id>"}` | A new itinerary, status `awaiting_approval` | `Replaying from checkpoint ...` warning, builder and later nodes run again, token usage line |
| 9 | **Persistence across restart** | Start a new trip (test 2), stop the server (Ctrl+C), start it again, then `GET /trips/{thread_id}` and resume | Same state returned; resume continues the same run | A fresh startup log, then the resume logs |

PowerShell versions of tests 2 to 8:

```powershell
# 2. start
$r = Call Post "/trips" '{"text":"5 days in Jaipur and Udaipur, 40000 INR, 2 people, love food and forts"}'
$r.status; $id = $r.thread_id

# 4. status
Call Get "/trips/$id" | ConvertTo-Json -Depth 10

# 5. request an edit
$r = Call Post "/trips/$id/resume" '{"approved": false, "feedback": "Make day 2 more relaxed"}'
$r.status; $r.revisions

# 6. approve
$r = Call Post "/trips/$id/resume" '{"approved": true}'
$r.status

# 7. history
$h = Call Get "/trips/$id/history"
$h | Select-Object step, next, checkpoint_id | Format-Table -AutoSize

# 8. rewind to the newest checkpoint that was about to run the builder
$cp = ($h | Where-Object { $_.next -contains "itinerary_builder" } | Select-Object -First 1).checkpoint_id
$r = Call Post "/trips/$id/rewind" (@{ checkpoint_id = $cp } | ConvertTo-Json)
$r.status
```

### 7.4 Clarification flow (missing information)

| # | Test | Request | Expected |
|---|---|---|---|
| 10 | Vague request | `POST /trips` `{"text":"plan me a trip"}` | `status: needs_input`, `questions` about cities and days; no research ran (no tool logs); `ask_user_node paused` |
| 11 | Answer the questions | `POST /trips/{id}/resume` `{"answer":"3 days in Jaipur and Udaipur, 30000 INR, 2 people, food and forts"}` | `status: awaiting_approval` with an itinerary; logs show `ask_user_node called` **a second time** (the node restarts on resume; this is expected) followed by `User answered the clarification` |
| 12 | Too few days | `POST /trips` `{"text":"3 cities Jaipur, Agra and Delhi in 2 days"}` | `needs_input` with the "too few days" question |
| 13 | Give-up path | Start with "plan me a trip" and answer with something still incomplete (for example "Jaipur") three times | After the third answer: `status: incomplete`, and the log shows `-> give_up` |

### 7.5 Loop and cap behaviour

| # | Test | Request | Expected |
|---|---|---|---|
| 14 | Validator loop | `POST /trips` `{"text":"5 days in Jaipur and Udaipur, budget 3000 INR, 2 people"}` | Reviewer errors in the logs, the builder retries (up to 3), and `warnings` shows "Unresolved after 3 attempts ..." if it never fits; `attempts: 3` |
| 15 | Revision cap | Ask for changes 3 times in a row | After the third change the response includes the "Maximum of 3 revisions reached" warning, and the next router decision is `done` |

### 7.6 Error handling

| # | Test | Request | Expected |
|---|---|---|---|
| 16 | Unknown trip | `GET /trips/doesnotexist` | `404 Trip not found` |
| 17 | Nothing waiting | `POST /trips/{id}/resume` on a completed trip | `409 This trip is not waiting for input.` |
| 18 | Wrong body for questions | Resume a `needs_input` trip with `{"approved": true}` | `422 'answer' is required ...` |
| 19 | Wrong body for approval | Resume an `awaiting_approval` trip with `{}` | `422 'approved' (true/false) is required.` |
| 20 | Rejection without feedback | `{"approved": false}` | `422 'feedback' is required when approved is false.` |
| 21 | Bad checkpoint | `POST /trips/{id}/rewind` `{"checkpoint_id":"nope"}` | `404 Checkpoint not found for this trip.` |
| 22 | Terminal checkpoint | Rewind to a checkpoint whose `next` is empty | `409 Nothing to re-run from that checkpoint.` |
| 23 | Empty body | `POST /trips` `{"text":""}` | `422` validation error (text must be at least 3 characters) |

### 7.7 What to check in the logs

| Look for | Confirms |
|---|---|
| `Router: ... -> city_allocator / ask_user / give_up` | The conditional edges are choosing correctly |
| Several `research_city_node called` lines with nearly the same timestamp | Cities run in parallel |
| `tool get_weather_forecast called with {...}` | Tool calls are logged with arguments |
| `node ... paused (waiting for human input)` | A real interrupt happened |
| `node ask_user_node called` twice for one question | Node restart on resume (expected) |
| `thread_id=... token usage: total=...` | Per-request token total, with the `reasoning` share |
| `Replaying from checkpoint ...` | A rewind re-ran LLM nodes and cost tokens |

### 7.8 Automated check (no LLM)

```powershell
uv run pytest
```

Covers the reviewer (`test_review.py`) and the two routers (`test_routing.py`). There are no HTTP-level tests yet, so the sections above are the manual test plan. When you add `TestClient` tests, use `with TestClient(app) as client:` so the lifespan runs, and mock the LLM and tools.

## 8. Key concepts learned (one line each)

| Concept | Note |
|---|---|
| uv, `package = false` | One tool for Python, venv and deps; app projects need no build system |
| Pydantic `BaseModel`, `Field(description=...)` | Typed DTO; the description is sent to the LLM as instructions |
| `with_structured_output` | Forces the LLM to return data matching a Pydantic class |
| State, node, edge, `compile()` | Shared object; function returning changed keys; fixed wire; frozen reusable runnable |
| Default overwrite vs reducer | A returned key replaces the old value unless the field has a reducer (`add_messages`, `merge_dicts`) |
| `@tool`, tool call, `bind_tools` | The LLM only **requests** calls; `ToolNode` runs them |
| ReAct loop | A graph cycle: LLM → tools → LLM, exits when the LLM answers in plain text |
| Conditional edge | A router function reads state and returns the next node's name |
| `Send` (map-reduce) and fan-in | One node run per item with a private payload; the next node runs once after all finish |
| Validator loop | Check, feed errors back, retry, always with a cap; errors retry, warnings inform |
| Decide in code, extract with the LLM | Required fields, sums and checks are deterministic Python |
| Reasoning models | Hidden thinking tokens drive latency; control with `reasoning_effort`, not temperature |
| Checkpointer | Saves a snapshot after every step; required for `interrupt` |
| `thread_id` | The unit of persistence: same thread, same history |
| `interrupt(payload)` | Pauses the run and returns the payload to the caller; payload must be JSON-serializable |
| `Command(resume=value)` | Becomes the return value of `interrupt()` and continues the same run |
| Node restarts on resume | Code before `interrupt()` runs again; keep it side-effect free; call `interrupt` once per node and loop with an edge |
| Checkpoint history / time travel | `aget_state_history` lists snapshots; `ainvoke(None, config_with_checkpoint_id)` replays from one and forks |
| `async with` saver | `AsyncSqliteSaver.from_conn_string(path)` owns an open DB connection; plain file path, folder must exist |
| Decorator factory | `@log_call("node")` calls a function that returns the decorator; `@log_call` without `()` breaks |
| Logging convention | Every module gets `logger = logging.getLogger(__name__)`; nodes get `@log_call("node")`, tools get `@log_call("tool", log_args=True)` under `@tool` |
| Pass `config` to nested runs | Keeps callbacks (token usage, tracing) visible inside sub-invocations |
| Tools return errors as text | The LLM can adapt; retry only temporary errors (timeouts, 429, 5xx) |

## 9. Lessons learned (bugs and fixes)

| Problem | Cause | Fix |
|---|---|---|
| `Expected a Python module at src\trip_planner\__init__.py` | `[build-system]` made uv build the project as a package | Remove `[build-system]` and `[project.scripts]`, add `[tool.uv] package = false` |
| `No module named 'app'` | Missing `__init__.py` in `app/` | Add `__init__.py` to every package folder, run from project root |
| `.env` got committed | `.gitignore` doesn't affect tracked files | `git rm --cached .env`, amend or recommit; rotate keys if pushed |
| Node output `None`; "Field required" | State key typo (`ininerary`) | Keep names identical across state, node, schema and API; use editor rename (F2) |
| `'State' object has no attribute 'graph'` | `lifespan` not attached or stale server | `FastAPI(..., lifespan=lifespan)`, restart, check startup log |
| Weather `503` | Open-Meteo outage | Retry helper, MET Norway fallback, `WEATHER_MOCK` switch |
| Places `403 robot policy` | Wikimedia needs a User-Agent with real contact info | Set `HEADERS` with app name and your email or repo URL |
| Places returned nothing | Parameter typo `grsearch` for `gsrsearch` | Compare the final URL with the docs |
| gpt-5-mini takes over a minute | Reasoning model; temperature ignored | Lower `reasoning_effort`; parallelise and batch tool calls |
| `AttributeError: 'list' object has no attribute 'city'` | Used the list name (`stays`) instead of the loop item (`stay`) | `for i, stay in enumerate(stays)` |
| `ValueError: No messages found in input state` | Node returned `{"message": ...}` instead of `{"messages": ...}` | Use the plural key |
| `AttributeError: 'dict' object has no attribute '__module__'` in `logging_config.py` | `@log_call` used without parentheses on `human_review_node`, so the function became the `kind` argument | Write `@log_call("node")`, or make the decorator accept both forms |

Recurring pattern: **misspelled keys, variable names and missing parentheses fail late and far from the cause.** Read the last lines of the traceback (they usually name the node: `During task with name '...'`) and search the codebase for the name.

## 10. Known limitations of the current system

| Limitation | Fixed in |
|---|---|
| No streaming; the first response takes a while | Phase 5 |
| City mini-graph is invoked from inside a node, not registered as a true subgraph | Phase 5 |
| No long-term memory of user preferences | Phase 5 |
| Grounding is only a warning; the LLM can still invent details | Phase 6 (output guardrail) |
| No input guardrails (off-topic, prompt injection) | Phase 6 |
| Concurrent resumes of the same thread aren't guarded | Phase 6 or 7 |
| SQLite suits one server process only | Phase 7 (Postgres checkpointer) |
| Anyone with a `thread_id` can resume it; no expiry or cleanup of old threads | Phase 7 (auth, cleanup) |
| Rewind can't change inputs (replay only) | Stretch: `graph.aupdate_state(checkpoint_config, {...})` then `ainvoke(None, ...)` |
| Costs are LLM estimates, not real prices | Accepted; budget check is a sanity check |
| Places come from Wikipedia search, so quality is uneven | Phase 7 (better source or RAG) |
| `convert_currency` is unused by the graph | Phase 6 or 7 |
| Pydantic models in checkpoints trigger "unregistered type" warnings | Optional: register them via `JsonPlusSerializer(allowed_msgpack_modules=[...])`; a list makes everything else strict (plain dicts), so list all models |
| No HTTP-level automated tests | Phase 6 or 7 |

## 11. Remaining phases in detail

| Phase | Build | Key concepts | Planned API additions | Done when... |
|---|---|---|---|---|
| **5** | Stream progress per node over SSE; long-term preferences (diet, budget style, pace) read at intake and written at the end; register the city research mini-graph as a real subgraph | `astream` modes (`updates`, `messages`), SSE, Store and namespaces, subgraphs and state mapping | `GET /trips/{id}/stream`, `GET/PUT /users/{id}/preferences` | Progress streams live; preferences persist across trips; subgraph works with `Send` and checkpoints |
| **6** | Input / tool / output guardrails; retries, fallbacks, timeouts; token-budget guardrail; request IDs, rate limiting; HTTP-level tests. Compare with provider-native guardrails | Guardrail nodes, grounding check, safe failure | Global error handlers | Bad inputs rejected; every stop grounded in tool results |
| **7** | Supervisor + Flight/Hotel/Activities agents; Booking handoff; agentic RAG (retrieve, grade, rewrite); image input; evals; LangSmith tracing; auth; Docker; Postgres checkpointer; deploy | Supervisor, handoffs, `Command(graph=Command.PARENT)`, agentic RAG, multimodal, evals, deployment | `POST /trips/{id}/book`, `POST /trips/{id}/upload`, `GET /trips/{id}/export`, `POST /auth/login` | Team plans, RAG answers visa questions, evals pass, runs in Docker |

## 12. Coverage map

| Concept | Phase | Status |
|---|---|---|
| Structured output | 0 | Done |
| State, nodes, edges, compile | 1 | Done |
| Tools, ReAct, conditional edges, `add_messages` | 2 | Done |
| `Send`, custom reducers, validator loop, retry cap | 3 | Done |
| Checkpointer, threads, `interrupt`, resume, time travel | 4 | Done |
| Streaming, Store, subgraphs | 5 | Next |
| Guardrails, error handling | 6 | Todo |
| Multi-agent, handoffs, agentic RAG, multimodal, evals, deployment | 7 | Todo |

## 13. Decisions and conventions

| Decision | Reason |
|---|---|
| Model and provider settings live in `.env`, not in code | Switch models with no code change |
| One shared LLM factory in `app/core/llm.py`; no reliance on `temperature` with gpt-5 | Single place to tune; temperature is silently dropped |
| Compile the graph once in `lifespan`, with the checkpointer, and reuse it | Avoid rebuild cost; the saver needs an open connection for the app's lifetime |
| `thread_id` = uuid4 hex per trip | Unguessable, so it also acts as a weak access token until real auth |
| Resume payloads are validated in the API before `Command(resume=...)` | A bad payload would otherwise break inside the node |
| Interrupt payloads are plain dicts and lists (`model_dump()`) | They must be JSON-serializable |
| Clarification answers are appended to `user_text` and re-parsed by `intake` | Reuses the extraction logic; loop is capped at 3 rounds |
| Human edit feedback reuses the builder's `validation_errors` path, with `attempts` reset to 0 | One feedback mechanism for reviewer failures and human edits |
| Caps everywhere: recursion limit, tool-call cap, `MAX_ATTEMPTS = 3`, `MAX_CLARIFY_ROUNDS = 3`, `MAX_REVISIONS = 3` | Bounded cost and no infinite loops |
| Required-field checks, day sums, budget totals and review checks in plain Python | Free, instant, consistent, unit-testable |
| Parallel results in a dict keyed by city with a merge reducer | Order independence and no duplicates on re-run |
| Grounding mismatch is a warning, not an error | Minor name differences shouldn't burn a retry |
| **Logging convention:** every new module has `logger = logging.getLogger(__name__)`; nodes use `@log_call("node")`; tools use `@log_call("tool", log_args=True)` under `@tool`; routers and endpoints log their decisions | Consistent "this node / tool was called" trail for debugging |
| Pass `config` into nested `ainvoke` calls | Callbacks and tracing see the nested LLM calls |
| Tools return errors as text; HTTP goes through `get_json()` with retry | The LLM can adapt and the request survives |
| Weather has a fallback and a labelled mock | A single free API outage must not block development |
| Scratch scripts named `scratch_*.py`; `data/` and `*.db` git-ignored | Keep local debugging and state out of git |
| Never commit `.env`; commit `.env.example` | Secrets safety |

## 14. Open items before Phase 5

| Item | Status |
|---|---|
| Run the HTTP walkthrough in section 7 (at least tests 2, 4, 5, 6, 7, 8, 9, 10, 11) | To confirm |
| Confirm `@log_call` is written with parentheses everywhere (command in section 6) and applied to all nodes and the four tools | To check |
| Update `.env.example` with `CHECKPOINT_DB=` and `LOG_LEVEL=` and the Azure variable names (empty values) | To do |
| `.gitignore` contains `data/` and `*.db`; `git status` shows no `.env` or `data/` | To check |
| `uv run pytest` passes (reviewer and routing tests) | To check |
| Negative-flow tests 12 to 23 in section 7 | Run before Phase 6 at the latest |
| Confirm Python version (`uv run python --version`) and pin 3.12 if you prefer | Optional |
| Commit: `git commit -m "phase 4: checkpointer, interrupts, resume, time travel, logging"` | To do |

## 15. Resume prompt (paste into a new session)

```
I'm building a LangGraph trip planner (2-3 cities, 5-day itinerary) with FastAPI,
uv, and Azure OpenAI gpt-5-mini (via ChatOpenAI with a base_url and
reasoning_effort; earlier I used Amazon Bedrock). I'm a beginner in Python and AI
agents but have 6 years of software engineering experience (Java/Spring Boot,
React, AWS). I prefer step-by-step plans with tables, plain-English
explanations, and exam tips. In every new file add logging (module logger,
@log_call("node") on nodes, @log_call("tool", log_args=True) under @tool,
and info logs for router decisions and endpoints).

Phases 0 to 4 are complete: structured intake; validate_request in plain Python;
ask_user as a real interrupt that loops back to intake (max 3 rounds);
city_allocator; parallel per-city research with Send, a merge_dicts reducer and a
per-city ReAct mini-graph with four tools; a builder with feedback; a plain-Python
reviewer with a retry loop capped at 3; a human_review interrupt for approve or
edit (max 3 revisions); an AsyncSqliteSaver checkpointer opened in the FastAPI
lifespan; endpoints POST /trips, GET /trips/{id}, POST /trips/{id}/resume,
GET /trips/{id}/history, POST /trips/{id}/rewind; token usage and node logging.
Structure, concepts, lessons, decisions and the /trips test guide are in
PROJECT_STATUS.md (pasted below).

Start Phase 5: add streaming of per-node progress over SSE (GET
/trips/{id}/stream, using astream with the updates and messages modes, and
working with the interrupt/resume flow), add long-term user preferences with a
LangGraph Store (read at intake, written at the end, GET/PUT
/users/{id}/preferences), and register the city research mini-graph as a real
subgraph that still works with Send and the checkpointer.

[paste the contents of PROJECT_STATUS.md here]
```