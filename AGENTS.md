# AGENTS.md

## Project

This repository implements a voice AI patient-registration system for a technical assessment.

A caller speaks with a Vapi voice agent. The agent collects and confirms patient demographics, then calls a FastAPI backend that validates and stores the patient. The REST API must also work independently of Vapi.

Use fake/test patient data only. This is not a production HIPAA system.

---

## Working Style

Work incrementally. Do not build the whole application in one change.

Before a meaningful change:

1. Inspect the relevant existing files.
2. Briefly explain what is being changed and why.
3. Identify the files that need modification.
4. Implement the smallest useful change.
5. Run the relevant verification or tests.
6. Explain how the change can be manually verified.

Preserve working behavior and follow existing project conventions.

Do not create files, abstractions, classes, or frameworks without a current need.

Prefer simple, conventional Python over clever or highly abstract solutions.

Do not rewrite working code without a concrete reason.

When a small ambiguity exists, choose the simplest reasonable option. Ask before making decisions with important architectural consequences.

Refer to "IMPLEMENTATION.md" for phases of implementation.

---

## Priorities

Optimize for:

1. Working end-to-end system
2. Correct persistent data
3. Natural voice interaction
4. Validation, errors, and traceability
5. Simple architecture
6. Tests and documentation
7. Bonus features

Do not introduce LangChain, LangGraph, Redis, Celery, RAG, vector databases, microservices, or custom STT/TTS unless a real requirement needs them.

---

## Stack

Use:

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL for deployment
- SQLite when useful for local development
- Alembic when migrations become necessary
- Vapi for telephony and voice AI
- pytest
- Railway for deployment

---

## Architecture

Keep responsibilities separate:

- **API routes** — HTTP requests, responses, status codes, and HTTPExceptions.
- **Pydantic schemas** — external input validation and serialization.
- **Services** — patient business logic and use cases.
- **SQLAlchemy models / DB modules** — persistence.
- **Voice modules** — Vapi tools and agent prompt.

The LLM must never execute SQL or directly access the database.

Create modules only when needed. A likely structure is:

```text
app/
    main.py
    api/
        patients.py
    schemas/
        patient.py
    models/
        patient.py
    services/
        patient_service.py
    db/
        session.py
    voice/
        tools.py
        prompt.py

tests/
```

This is a guideline, not a required structure.

---

## Patient Model

Required fields:

* `first_name`
* `last_name`
* `date_of_birth`
* `sex`
* `phone_number`
* `address_line_1`
* `city`
* `state`
* `zip_code`

Optional fields:

* `email`
* `address_line_2`
* `insurance_provider`
* `insurance_member_id`
* `preferred_language`
* `emergency_contact_name`
* `emergency_contact_phone`

`preferred_language` defaults to English.

Generated fields:

* `patient_id` — UUID
* `created_at` — UTC timestamp
* `updated_at` — UTC timestamp
* `deleted_at` — nullable UTC timestamp

### Validation

The backend is the source of truth for validation.

Enforce:

* Names: 1–50 characters; letters, hyphens, and apostrophes.
* DOB: valid date and not in the future.
* External DOB format: `MM/DD/YYYY`.
* Sex: `Male`, `Female`, `Other`, or `Decline to Answer`.
* Phone: valid U.S. 10-digit number and consistently normalized.
* State: valid two-letter U.S. abbreviation.
* ZIP: 5-digit or ZIP+4.
* Email: valid when provided.

Never invent missing values or silently fix uncertain input.

Never save an incomplete or unconfirmed voice registration.

Deletion is always soft deletion using `deleted_at`. Normal reads must exclude deleted patients.

---

## API

Required endpoints:

* `GET /patients`
* `GET /patients/{patient_id}`
* `POST /patients`
* `PUT /patients/{patient_id}`
* `DELETE /patients/{patient_id}`

`GET /patients` supports optional filters:

* `last_name`
* `date_of_birth`
* `phone_number`

`PUT` supports partial updates.

`DELETE` performs a soft delete.

Use this response shape:

```json
{
  "data": {},
  "error": null
}
```

Errors use:

```json
{
  "data": null,
  "error": {
    "message": "..."
  }
}
```

Use correct HTTP status codes such as `200`, `201`, `400`, `404`, `422`, and `500`.

Never hide failures behind HTTP 200.

---

## Errors and Traceability

Every important operation must be traceable.

Failures must never disappear silently.

### Logging

Use Python's standard `logging` module throughout the application.

Add useful logs at important boundaries and state changes, including:

* incoming API operations
* service operations
* database operations
* patient creation attempts
* patient updates and soft deletes
* validation failures
* Vapi tool calls
* external service calls
* successful important operations
* unexpected exceptions

Use appropriate levels:

* `DEBUG` — useful development details
* `INFO` — normal important operations
* `WARNING` — recoverable or suspicious situations
* `ERROR` / `EXCEPTION` — failed operations and unexpected exceptions

When handling an unexpected exception, log enough context to trace where and why it failed. Use `logger.exception(...)` when a stack trace is useful.

Do not log secrets, credentials, or unnecessary patient data.

Do not use `print()` for application diagnostics.

### Exceptions

Do not silently catch exceptions.

Use exceptions intentionally:

* **Pydantic validation** for request/schema validation.
* **ValueError** for invalid values or domain/service-level input that cannot be accepted.
* **HTTPException** at the FastAPI/API boundary for HTTP-specific failures.
* Database or external-service exceptions should be logged and translated into meaningful application/API failures where appropriate.

Do not raise `HTTPException` deep inside database or domain code unless that code specifically belongs to the HTTP layer.

Do not use broad `except Exception:` blocks unless they are needed at an application boundary. If one is necessary:

1. Log the exception with context and traceback.
2. Return or raise an appropriate failure.
3. Never silently continue as if the operation succeeded.

Error messages should explain what failed without exposing secrets or internal implementation details.

A failure should be traceable through:

```text
API / Vapi request
        ↓
service operation
        ↓
database / external operation
        ↓
success or logged exception
        ↓
meaningful response
```

---

## Voice Agent

Keep Vapi tools small. Core operations should be similar to:

* `search_patient_by_phone`
* `create_patient`
* `update_patient`

The agent should:

* accept information in any order
* remember already supplied fields
* ask only for missing required information
* handle corrections
* allow the caller to start over
* offer optional fields after required fields
* read the completed information back
* ask for explicit confirmation
* save only after confirmation
* clearly communicate backend failures

A dropped call must not accidentally save an unconfirmed patient.

Duplicate detection, transcripts, multilingual support, appointment scheduling, and dashboards are bonuses. Do not implement them before the core flow works.

---

## Security and Configuration

Load secrets and configuration from environment variables.

Never commit:

* API keys
* database credentials
* Vapi credentials
* LLM credentials

Maintain `.env.example` when configuration variables are introduced.

Validate all external input.

Use database constraints for important invariants where reasonable.

---

## Testing

Add focused tests for important behavior.

Prioritize:

* valid patient creation
* invalid DOB
* invalid phone number
* invalid ZIP
* retrieval
* filtering
* partial updates
* soft deletion
* exclusion of deleted patients
* expected error paths

Test failure behavior as well as success behavior.

Run the narrowest relevant tests first, then the full suite when practical.

For API changes, provide a simple manual verification using `/docs`, `curl`, or an equivalent request.

Never claim a test or command passed unless it was actually executed.

If verification cannot be performed, state why.

---

## Implementation Order

Unless the existing code requires otherwise:

```text
Project setup
    ↓
Pydantic schemas
    ↓
SQLAlchemy + database
    ↓
Patient service
    ↓
REST API
    ↓
Backend tests
    ↓
Deployment
    ↓
Vapi integration
    ↓
Voice prompt
    ↓
End-to-end phone test
    ↓
Edge cases / bonuses
```

The backend should work independently before Vapi is connected.

---

## Definition of Done

The core system is complete when:

1. A caller calls the phone number.
2. Vapi conducts a natural registration conversation.
3. Required patient information is collected and validated.
4. Corrections and invalid values are handled.
5. The complete information is read back.
6. The caller explicitly confirms it.
7. Vapi calls the backend.
8. The backend validates and persists the patient.
9. The caller receives a success or meaningful failure message.
10. The patient remains after server restarts.
11. The patient can be retrieved through the REST API.
12. Important operations and failures can be traced through logs.
