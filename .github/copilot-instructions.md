# GitHub Copilot instructions

This is a Python 3.12+ FastAPI project for voice-based patient registration. Vapi owns telephony, STT/TTS, turn-taking, and LLM invocation. The backend owns validation, business rules, SQLAlchemy persistence, and a REST API.

## Coding guidance

- Make small, milestone-scoped changes; do not scaffold the entire planned application at once.
- Inspect nearby code and follow established conventions before suggesting changes.
- Prefer straightforward, typed Python and small functions over generic repositories, framework-heavy patterns, or premature abstractions.
- Keep HTTP handling, Pydantic schemas, service logic, SQLAlchemy persistence, and voice integration separated.
- Do not introduce LangChain, LangGraph, Redis, Celery, RAG, vector databases, microservices, or custom STT/TTS without an explicit requirement.
- Use environment variables for credentials and secrets. Never hardcode or log them.
- Use standard Python logging and avoid logging unnecessary patient information.

## Domain invariants

- Required fields: `first_name`, `last_name`, `date_of_birth`, `sex`, `phone_number`, `address_line_1`, `city`, `state`, and `zip_code`.
- Optional fields: `email`, `address_line_2`, `insurance_provider`, `insurance_member_id`, `preferred_language`, `emergency_contact_name`, and `emergency_contact_phone`.
- Generate UUID `patient_id` plus UTC `created_at`, `updated_at`, and nullable `deleted_at`.
- Validate all input in the backend regardless of any LLM-side validation.
- Reject future dates of birth, invalid US phone numbers, invalid state abbreviations, invalid ZIP codes, and invalid supplied email addresses.
- Preserve proper date/UUID types internally; conversational DOB formatting is `MM/DD/YYYY`.
- Never invent missing patient data or persist a voice registration before explicit caller confirmation.
- Patient deletion is always soft deletion via `deleted_at`. Normal queries exclude deleted rows.

## API behavior

Support `GET /patients` with optional `last_name`, `date_of_birth`, and `phone_number` filters; `GET /patients/{patient_id}`; `POST /patients`; partial `PUT /patients/{patient_id}`; and soft `DELETE /patients/{patient_id}`.

Responses use either `{ "data": ..., "error": null }` or `{ "data": null, "error": { "message": "..." } }`, with meaningful HTTP status codes rather than HTTP 200 for every outcome.

## Tests

Use pytest for high-value behavior. Prioritize creation, validation failures, retrieval/filtering, partial update, soft delete, and ensuring deleted patients are absent from normal reads. Keep tests readable and focused; do not chase exhaustive coverage at the expense of the working end-to-end flow.

The project uses fake/test patient data and is an assessment demo, not a claim of production HIPAA compliance.
