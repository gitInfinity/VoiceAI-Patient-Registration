# Voice AI Patient Registration

A complete demonstration of phone-based patient registration using Vapi, FastAPI,
SQLAlchemy, and PostgreSQL. The voice assistant gathers fake demographic data,
reads it back for explicit confirmation, and invokes authenticated backend tools to
search, create, or update a patient. The REST API can also be used independently.

> This is an assessment project, not a HIPAA-compliant clinical system. Use fake
> patient information only.

## Live application

- API: `https://intakemd.up.railway.app`
- Interactive documentation: `https://intakemd.up.railway.app/docs`
- Readiness check: `https://intakemd.up.railway.app/health`

## How it works

```text
Caller
  │ voice conversation
  ▼
Vapi assistant ── authenticated tool call ──► FastAPI
                                                  │
                                                  ▼
                                          patient service
                                                  │
                                                  ▼
                                         PostgreSQL / SQLite
```

Vapi owns telephony, transcription, speech synthesis, interruptions, and model tool
selection. FastAPI remains the source of truth for validation and persistence; the
language model never accesses the database directly.

## Features

- Natural, interruption-friendly collection of required and optional demographics
- Caller corrections, out-of-order answers, draft reset, and focused clarification
- Full readback and explicit confirmation before both create and update operations
- Duplicate lookup by normalized US phone number
- Backend validation for names, date of birth, sex, phone, state, ZIP, and email
- UUID patient identifiers and UTC timestamps
- PostgreSQL deployment with Alembic migrations; SQLite for local development
- Filterable REST CRUD API with partial updates and soft deletion
- Authenticated Vapi tools using a dedicated `X-Vapi-Secret` credential
- Consistent response envelopes, correlation IDs, structured request logs, and safe
  error handling that does not expose secrets or request bodies
- Focused automated coverage for schemas, models, services, API behavior, migrations,
  assistant configuration, and voice tools

## What I debugged

Building the complete call path exposed several integration failures that were not
visible when testing each component by itself. These were the significant problems,
their causes, and their resolutions:

| Symptom | Root cause | Resolution |
| --- | --- | --- |
| `/health` and `/docs` worked, but every patient route returned HTTP 500 | The application was running without the deployed patient table | Added an Alembic migration and configured `alembic upgrade head` as Railway's pre-deploy command |
| Railway initially connected to SQLite instead of PostgreSQL | No PostgreSQL service existed in the Railway project, so the application used its local SQLite default | Added Railway PostgreSQL and connected the application through `DATABASE_URL` |
| Deployment crashed with `Could not parse SQLAlchemy URL` | `${{Postgres.DATABASE_URL}}` referenced a nonexistent service and resolved to an empty value | Used the exact Railway database service name and verified that its `DATABASE_URL` variable existed |
| A Docker startup change did not run in Railway | A Railway custom Start Command overrode the image command | Kept migrations in the pre-deploy command and used Uvicorn alone as the application Start Command |
| `POST /voice/tools` did not appear in the public OpenAPI documentation | Railway was serving an older commit that did not include the voice router | Verified the deployed commit, redeployed, and confirmed router registration in `/docs` |
| Vapi assistant configuration was rejected despite a valid private key | The Vapi API rejected the default script request identity | Added explicit JSON headers and a stable `User-Agent` to the configuration client |
| Vapi reached `/voice/tools` but received `Invalid voice tool credentials` | The Custom Credential added `Bearer ` before the token, while the backend expected the raw `X-Vapi-Secret` value | Configured a Bearer Token credential with header `X-Vapi-Secret` and disabled the Bearer prefix |
| Valid phone numbers were requested repeatedly after successful search calls | The webhook returned an object in `result`; Vapi custom tools require a single-line string result | Serialized every result as compact JSON text and added regression tests for the response type |
| Tool calls displayed as completed but creation still returned `Request validation failed` | Vapi sent nested function calls with JSON-encoded arguments, while the webhook expected flattened dictionary arguments | Normalized Vapi's current nested payload and the compatible flattened `parameters` shape at the schema boundary |
| The editor warned that the lifespan context manager return annotation was deprecated | An async context manager was annotated as an `AsyncIterator` | Changed the lifespan annotation to `AsyncGenerator[None, None]` |

The phone-number issue was especially instructive: Vapi displayed the HTTP tool call
as completed, but the model could not reliably consume its object-valued result.
Testing the entire caller → Vapi → authenticated webhook → service → database path
was necessary to distinguish transport success from a correctly interpreted tool
response.

## Technology

- Python 3.12+
- FastAPI and Pydantic
- SQLAlchemy 2 and Alembic
- PostgreSQL in Railway; SQLite locally
- Vapi for the voice assistant and function tools
- pytest and HTTPX for testing
- `uv` for dependency and environment management

## Repository layout

```text
app/
  api/                 REST and Vapi HTTP routes
  db/                  engine, session, and database checks
  models/              SQLAlchemy patient model
  schemas/             external validation and response models
  services/            patient persistence use cases
  voice/               version-controlled assistant prompt and tool definitions
  config.py             environment configuration
  main.py               FastAPI application and exception handlers
  observability.py      request IDs and logging configuration
migrations/             Alembic environment and revisions
scripts/configure_vapi.py
tests/
Dockerfile
```

## Local development

### Prerequisites

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/)

Clone the repository, create local configuration, install dependencies, migrate the
database, and start the API:

```powershell
Copy-Item .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

SQLite is used at `./voice_agent.db` unless `DATABASE_URL` is changed. Open
`http://127.0.0.1:8000/docs` to exercise the API.

### Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | No locally | SQLAlchemy database URL; defaults to local SQLite |
| `LOG_LEVEL` | No | Python logging level; defaults to `INFO` |
| `VAPI_API_KEY` or `PRIVATE_VAPI_KEY` | For Vapi configuration | Private Vapi API key |
| `VAPI_ASSISTANT_ID` | After assistant creation | Existing assistant to update |
| `VAPI_TOOL_SECRET` | For voice tools | Random secret checked in `X-Vapi-Secret` |
| `VAPI_CREDENTIAL_ID` | For Vapi configuration | Vapi Custom Credential ID containing the tool secret |
| `PUBLIC_BASE_URL` | For Vapi configuration | Public API origin, without a trailing path |

Generate the tool secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Never commit `.env`. The repository ignores it and provides only safe placeholders
in `.env.example`.

## REST API

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/health` | Verifies the API and database connection |
| `GET` | `/patients` | Lists active patients; supports exact filters |
| `GET` | `/patients/{patient_id}` | Retrieves one active patient |
| `POST` | `/patients` | Validates and creates a patient |
| `PUT` | `/patients/{patient_id}` | Applies a validated partial update |
| `DELETE` | `/patients/{patient_id}` | Soft-deletes a patient |
| `POST` | `/voice/tools` | Executes authenticated Vapi tool calls |

Patient list filters are `last_name`, `date_of_birth`, and `phone_number`. Normal
reads exclude soft-deleted records. API responses use one envelope:

```json
{
  "data": {},
  "error": null
}
```

Failures use an appropriate non-2xx status and place a safe message in `error`.
Every response includes `X-Request-ID`; the same value appears in server logs.

### Create a fake patient

```powershell
$body = @{
    first_name = "Anne"
    last_name = "Smith"
    date_of_birth = "04/15/1990"
    sex = "Female"
    phone_number = "(212) 555-0198"
    address_line_1 = "123 Main Street"
    city = "New York"
    state = "NY"
    zip_code = "10001"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://127.0.0.1:8000/patients `
    -ContentType application/json `
    -Body $body
```

## Vapi setup

The checked-in assistant definition contains the production conversation policy and
three functions:

- `search_patient_by_phone`
- `create_patient`
- `update_patient`

Creation and update both require `confirmed=true`. The backend independently rejects
either operation without explicit confirmation, even if the model invokes a tool
incorrectly.

1. Deploy the API and set a random `VAPI_TOOL_SECRET` in the application environment.
2. In Vapi, create a Bearer Token Custom Credential with header `X-Vapi-Secret`, the
   same raw token, and the Bearer prefix disabled.
3. Set `PUBLIC_BASE_URL`, `VAPI_CREDENTIAL_ID`, and the private Vapi key in local
   `.env`.
4. Preview the assistant payload, then apply it:

   ```powershell
   uv run python -m scripts.configure_vapi
   uv run python -m scripts.configure_vapi --apply
   ```

5. If the script creates an assistant, save the returned ID as
   `VAPI_ASSISTANT_ID`. Future runs update that assistant instead of creating a
   duplicate.
6. Attach a Vapi or imported phone number to the assistant in the Vapi dashboard.

The tool server URL is derived as `${PUBLIC_BASE_URL}/voice/tools`. Tool arguments and
credentials are deliberately omitted from application logs. Responses use Vapi's
required `results` envelope with each tool result serialized as a compact single-line
JSON string.

## Railway deployment

The root `Dockerfile` starts Uvicorn on Railway's injected `PORT`. A recommended
Railway application configuration is:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
LOG_LEVEL=INFO
VAPI_TOOL_SECRET=<random-dedicated-secret>
```

Use the exact database service name in the reference. Configure this pre-deploy
command so a migration failure stops the release cleanly:

```shell
alembic upgrade head
```

Set `/health` as the health-check path. Keep PostgreSQL private; the application
uses Railway's internal service connection. `postgres://` and `postgresql://` URLs
are normalized to SQLAlchemy's psycopg 3 driver automatically.

## Verification

Run all automated tests:

```powershell
uv run pytest
```

For an end-to-end voice check, call the attached number with fake details and test:

1. A confirmed registration creates exactly one active row.
2. Saying no at final confirmation creates no row.
3. A repeated phone number is found before another create attempt.
4. A correction is read back and only updates after explicit confirmation.
5. A backend validation or availability failure is reported as an unsuccessful save.

Confirm persisted results through `/docs` or `GET /patients`, then soft-delete any
temporary records.

## Safety and scope

This repository intentionally avoids a custom speech stack and delegates voice
infrastructure to Vapi. It does not implement production healthcare controls such as
HIPAA compliance, identity verification, authorization roles, audit retention,
encryption policy management, or consent workflows. Do not use it with real patient
or protected health information.
