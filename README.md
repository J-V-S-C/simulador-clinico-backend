# Simulador Clínico — Python backend

Educational clinical simulation API for the FIAP Hospital Moinhos de Vento challenge. The Python server owns cases, elapsed time, patient state, Gemini evaluation, reports, authentication, and persistence. The Next.js frontend in `../Simulador-Clinico-Front-End/` consumes the JSON API. The old Streamlit and mocked LLM demonstrations have been removed; the API uses the configured Gemini integration.

This is a fictional learning simulation, not clinical decision support. Use fictional or anonymized case data.

## Requirements and setup

Use Python 3.12 or newer. From `backend/`:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

For an API installation, install `requirements.txt`. Test-only dependencies are in `requirements-dev.txt`.

Set these names in `backend/.env` or your server environment. The server loads `.env` automatically; do not expose it to the frontend or commit it. See `.env.example` for the names. Gemini reads `GEMINI_API_KEY` or `GOOGLE_API_KEY` (the latter takes precedence). The default model is `gemini-3.5-flash-lite`; `GEMINI_MODEL` can override it. If the key is absent, the server still starts, but interaction requests return `503` without changing the simulation. No test needs a live Gemini key.

```bash
.venv/bin/python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Open the interactive API documentation at **`http://127.0.0.1:8000/docs`**. Opening `http://127.0.0.1:8000/` redirects there. API endpoints start with `/api`; for example, the health check is `http://127.0.0.1:8000/api/health`. The OpenAPI JSON is at `http://127.0.0.1:8000/openapi.json`.

The documentation shows the route list by default. The long Models section is hidden and response model details start collapsed. Swagger UI still shows an endpoint's Responses section when you open that endpoint; it has no built-in setting to hide only that section.

The default SQLite database is `data/clinical.db`. The server applies Alembic migrations and imports existing `data/diseases.csv`, `data/simulations.csv`, and `data/reports.csv` idempotently. Imported student attempts belong to a disabled archive account; new accounts cannot access another student's data. Keep a backup of CSV files before a deployment migration.

The API refreshes the built-in case templates on startup without changing completed or running attempts. New attempts include introductory fever, cold, and dizziness cases plus the existing chest-pain case. The case list names the presenting complaint without revealing the final diagnosis. Each introductory template has a main complaint and draws one of two additional symptoms for each attempt; some additional symptoms start hidden. Asking the patient about other symptoms can reveal one, and any remaining hidden complaint appears when all visible complaints have been addressed. A correct conduct addresses its selected symptom once; the same text cannot be reused for another symptom. When every selected complaint is addressed, the simulation ends immediately with `Atendimento bem-sucedido`, resolved symptoms and stable final vital signs. This is a pedagogical completion state, not a claim that real symptoms disappear immediately. Partial conducts can improve the measurements without completing the complaint; delay continues to worsen active symptoms. The beginner protocol references are the NHS pages for [fever](https://www.nhs.uk/symptoms/fever-in-adults/), [common cold](https://www.nhs.uk/conditions/common-cold/), [dizziness](https://www.nhs.uk/symptoms/dizziness/) and [dehydration](https://www.nhs.uk/conditions/dehydration/).

The CSV import is a migration path for earlier saved data; new sessions use the configured SQL database.

## API routes

### Feedback da experiência

Após a conclusão de cada tentativa, o frontend oferece uma pesquisa opcional: gostei/não gostei, clareza (1–5), dificuldade (1–5), recurso mais útil e sugestão de melhoria. `POST /api/simulations/{id}/experience-feedback` cria uma resposta por tentativa concluída; `GET` permite ao próprio estudante ver se já respondeu; `PUT` permite editar a resposta. Todas exigem autenticação e verificam a propriedade da tentativa. Os dados ficam na tabela `experience_feedback`, criada pela migração Alembic. O diálogo pode ser dispensado e reaberto na página de resultado.

Para analisar respostas no servidor, execute `.venv/bin/python feedback_summary.py` com `DATABASE_URL` apontando para o banco usado pela API. O script mostra total, proporção positiva, médias e distribuição das notas, além das sugestões de melhoria. Revise comentários livres antes de publicá-los e use apenas resultados agregados no relatório. Esta pesquisa espontânea complementa, mas não substitui, o teste observado com três participantes exigido pela disciplina.

All routes use `/api`. Except health, registration, and login, send `Authorization: Bearer <access_token>`. Tokens expire after eight hours; logout revokes them. The React app must keep the token outside the URL and call `/auth/me` when checking its private area.

In `/docs`, call `POST /api/auth/login`, copy the `access_token` value, then click **Authorize** at the top of the page. Paste only the token (no `Bearer` prefix or quotes) and click **Authorize**. Swagger UI adds the `Bearer` prefix to protected requests automatically. If you enter a header manually, use `Authorization: Bearer <access_token>`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Database readiness |
| POST | `/auth/register` | Create student account |
| POST | `/auth/login` | Obtain bearer token |
| POST | `/auth/logout` | Revoke token |
| GET | `/auth/me` | Current student |
| GET | `/cases` | Case summaries without diagnosis |
| GET | `/cases/{case_id}` | Case setup limits |
| POST | `/simulations` | Start a timed simulation |
| GET | `/simulations` | List own attempts |
| GET | `/simulations/{id}` | Current state and history |
| POST | `/simulations/{id}/interactions` | Ask or treat; Gemini replies and classifies |
| POST | `/simulations/{id}/interactions/stream` | Stream provisional patient text, then return the persisted interaction |
| POST | `/simulations/{id}/time/advance` | Advance simulated seconds (`{"seconds": 30}`, 1–600) |
| POST | `/simulations/{id}/protocols/{symptom_name}/reveal` | Reveal the next protocol level |
| POST | `/simulations/{id}/reports` | Report a stored interaction by ID |
| POST | `/simulations/{id}/finish` | End the attempt; server computes outcome |
| GET | `/simulations/{id}/result` | Final result |

OpenAPI contains the exact request and response schemas. A typical flow is register → login → list cases → start → interact/reveal/advance → report if needed → finish or automatic ending → result. The interaction request contains `student_text` and a visible `symptom_name`. It never accepts a client supplied classification or outcome. Reports contain `interaction_id` and `description`; the server retrieves the AI text and context. Validation failures use HTTP `422`; domain and external failures return `{ "error": { "code": "...", "message": "..." } }` with an appropriate status.

The clock advances by elapsed wall-clock seconds when an attempt is read or changed. The explicit advance route adds simulated seconds. A case ends at its time limit or when a vital sign becomes critical. Closing the browser does not pause the timer. The API hides the case diagnosis until the result exists. Interaction history records Gemini input/output token counts for usage review.

Current attempts offer 1, 3, 5 or 10 minutes (5 by default). Natural symptom and vital-sign evolution is reconciled each elapsed second and scales to the chosen limit. Pressure grows while the student takes no effective action; a correct or partially correct interaction lowers the subsequent rate, which then rises again over time. Manual time advance uses the same model and can be configured by the student in the frontend. New students can start with the introductory fever and headache case. The coronary case remains available. The values are fictional teaching parameters, not medical predictions. Existing saved attempts retain their original case snapshot. New accounts store a chosen display name; existing accounts display "Estudante" until a profile-edit feature is provided.

Simulation state also returns `protocols` with the revealed content for each visible symptom. The React app uses this state after reload; a reveal request advances one level and the app then refreshes the simulation. To run the UI locally, follow the [frontend README](../Simulador-Clinico-Front-End/README.md) and keep this API running on port 8000.

Each protocol has three teaching levels: initial orientation, a more direct hint, and the complete expected conduct. A message can be partial when it covers only some level-3 elements; an exact copy of the full level-3 conduct is classified as correct even if Gemini returns a different classification. Questions, observation, measurement, and reassessment alone receive `assessment`: they can reveal patient information but do not lower symptom intensity, slow worsening, or mark a complaint as resolved. A concrete intervention is required for `correct` or `partially_correct`; other wording is assessed by Gemini, so borderline paraphrases can still need review. The simulation response includes `reference_source` for every visible symptom, and the UI links it in the protocol drawer and result. All built-in cases are adapted from one public source portal, the [NHS Health A to Z](https://www.nhs.uk/conditions/): [fever](https://www.nhs.uk/symptoms/fever-in-adults/), [headaches](https://www.nhs.uk/symptoms/headaches/), [common cold](https://www.nhs.uk/conditions/common-cold/), [sore throat](https://www.nhs.uk/symptoms/sore-throat/), [dizziness](https://www.nhs.uk/symptoms/dizziness/), [dehydration](https://www.nhs.uk/conditions/dehydration/), and [heart attack](https://www.nhs.uk/conditions/heart-attack/). The cardiac teaching case now prioritizes emergency escalation, rest, and observation instead of generic analgesia or routine oxygen. These are simplified educational hints, not a locally approved clinical protocol; a clinician should review them before institutional use. Case templates refresh on API startup; existing attempts retain their saved snapshot and grading.

## Code organization

- `server.py`: FastAPI app, CORS, dependency composition, error translation.
- `routes/`: URL declarations and Pydantic API schemas.
- `handlers/`: authentication and HTTP to service bridge.
- `services/`: auth, case, simulation, and report use cases.
- `ports/`: repository, clock, and evaluator interfaces.
- `repositories/`: SQLAlchemy mappings, transactions, CSV import, and existing CSV demo repositories.
- `models/`: clinical state and transitions, independent of FastAPI and Gemini.
- `integrations/gemini.py`: official `google-genai` adapter with validated structured output.
- `migrations/`: Alembic history.

A single persistent VPS can run FastAPI and SQLite together; Supabase is optional. Set `DATABASE_URL=sqlite:////var/lib/simulador/clinical.db` (four slashes before an absolute path), create the directory with write permission for the API process, and keep the database on local persistent storage outside the checkout. Use a consistent `WorkingDirectory` for the service, or an absolute URL as above. The server applies Alembic migrations on startup. Put the API behind an HTTPS reverse proxy and point `NEXT_PUBLIC_API_BASE_URL` to its public `/api` URL. The Next.js frontend may run on the same VPS or on Vercel. Set `ALLOWED_ORIGINS` to the exact frontend origin. Add deployment rate limits for login and Gemini-backed interactions before exposing the API publicly. The Gemini call has a 15-second timeout and returns `503` on failure.

SQLite permits one writer at a time; this is a reasonable starting point for a single VPS with modest traffic and short database transactions. Keep the database off network filesystems and ephemeral container layers. Schedule consistent backups with SQLite's backup API or `sqlite3 .backup`, copy those backups off the VPS, and test a restore. If concurrent writes cause lock errors or the API later runs on multiple servers, migrate to PostgreSQL. Supabase Postgres remains an option: keep its `postgresql+psycopg://` URL with `sslmode=require` in the backend-only `DATABASE_URL`. For an IPv4-only persistent backend, use Supabase's session pooler; for IPv6, a direct connection is available.

For a no-cost Vercel + Oracle VPS deployment checklist, see [DEPLOY_ORACLE_VERCEL.md](DEPLOY_ORACLE_VERCEL.md). SQLite uses WAL mode on local file databases so readers can run while one write commits; it still permits only one writer at a time.

The stream route sends `preview` events with provisional patient text, followed by one `complete` event containing the saved interaction and latest simulation state. On failure it sends `error`, and no partial response is saved. The original JSON interaction route remains available. Streaming improves the time until text appears; the total evaluation time still depends on Gemini and network latency.

## Tests

From `backend/`:

```bash
.venv/bin/python -m pytest -q tests
```

The suite is organized by service: `test_auth_service.py`, `test_case_service.py`, `test_simulation_service.py`, `test_report_service.py`, and `test_presentation.py`. Each test uses fresh dependencies from `tests/fakes/`: an in-memory store, a controllable clock, and a fake evaluator. No database files or Gemini requests are created by the service tests. Authentication tests cover password hashing, invalid credentials, token expiration, and logout.

## Backups and rollback

Before changing an existing installation, make a consistent SQLite backup with `sqlite3 .backup` or the Python backup API and back up the CSV files. Schema changes are applied by Alembic; use the matching migration revision when rolling back code.
