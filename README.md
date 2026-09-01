# Voice AI Patient Registration

A FastAPI backend for a voice-based patient registration assessment. The REST API will validate and persist patient data, while Vapi will handle telephony and conversational voice behavior.

The backend currently provides validated patient CRUD operations with soft deletion. Voice integration will be added incrementally after backend deployment.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Local setup

Install dependencies:

```shell
uv sync
```

Copy `.env.example` to `.env` if you want to override the local defaults, apply the database migration, then start the API:

```shell
uv run alembic upgrade head
```

```shell
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the generated API documentation or request the health endpoint:

```shell
curl http://127.0.0.1:8000/health
```

## Tests

```shell
uv run pytest
```

## Manual API verification

Start the server, then create a fake patient from another terminal:

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

$created = Invoke-RestMethod `
    -Method Post `
    -Uri http://127.0.0.1:8000/patients `
    -ContentType "application/json" `
    -Body $body

$created
Invoke-RestMethod http://127.0.0.1:8000/patients
Invoke-RestMethod "http://127.0.0.1:8000/patients?phone_number=212-555-0198"
```

Every response includes `data` and `error`. Every HTTP response also includes an `X-Request-ID` header that can be matched to server logs. Request logs contain the HTTP method, path, status, duration, and correlation ID but intentionally omit bodies and query values.

SQLite is the local default. Deployment will set `DATABASE_URL` to PostgreSQL through environment configuration.

## Railway deployment

The repository includes a production `Dockerfile`. Railway detects a root-level Dockerfile automatically, so no legacy `railway.toml` or `railway.json` is needed.

1. Push the repository to GitHub and create a Railway project.
2. Add a managed PostgreSQL service to the project.
3. Add an application service from the GitHub repository.
4. In the application service's Variables tab, set:

   ```text
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   LOG_LEVEL=INFO
   ```

   If the database service has a different name, use that service name in the reference.

5. Set the application's pre-deploy command to:

   ```shell
   alembic upgrade head
   ```

6. Set the health-check path to `/health` and a suitable timeout such as 120 seconds.
7. Generate a public domain from the application's Networking settings.
8. Verify `https://<generated-domain>/health`, `/docs`, and a fake patient CRUD flow.

The Docker command binds Uvicorn to `0.0.0.0` and Railway's injected `PORT`. The application converts Railway-style `postgres://` or `postgresql://` URLs to SQLAlchemy's psycopg 3 dialect automatically.

Do not expose the PostgreSQL service publicly for normal application operation. The application should use Railway's private service reference. Do not put database credentials or Vapi keys in repository files.

## Vapi assistant bootstrap

Phase 8 begins with a version-controlled assistant definition. Preview it without making an external change:

```shell
uv run python -m scripts.configure_vapi
```

After setting a private `VAPI_API_KEY`, create the assistant explicitly:

```shell
uv run python -m scripts.configure_vapi --apply
```

Save the returned ID as `VAPI_ASSISTANT_ID`. Subsequent `--apply` runs will update that assistant instead of creating another one. The bootstrap assistant intentionally has no backend tools and will never claim it saved a registration. Patient creation is connected in Phase 9.
