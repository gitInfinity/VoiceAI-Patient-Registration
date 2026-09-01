# Implementation.md

## Implementation Phases — Voice AI Patient Registration System

Unless the existing repository suggests otherwise, development proceeds approximately in this order. The REST/backend should work independently before the voice agent is connected.

---

### Phase 1
Project skeleton + dependencies + configuration

### Phase 2
Patient Pydantic schemas and validation

### Phase 3
SQLAlchemy patient model + database connection

### Phase 4
Patient service layer

### Phase 5
REST API CRUD endpoints

### Phase 6
Test the API independently

### Phase 7
Deploy backend/database

### Phase 8
Configure Vapi assistant

### Phase 9
Implement Vapi → backend tool calls

### Phase 10
Design/refine voice agent system prompt

### Phase 11
End-to-end phone testing

### Phase 12
Edge cases, README, tests and optional bonuses

---

**Guiding principle:** the backend must be fully functional and independently testable before the voice agent (Vapi) is wired in. Each phase should be completed and verified before moving to the next.