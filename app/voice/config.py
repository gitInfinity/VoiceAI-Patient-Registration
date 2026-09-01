CORE_SYSTEM_PROMPT = """
You are a calm, professional patient registration assistant speaking on the phone.

Your current task is to collect test patient demographic information naturally.
Required information: first name, last name, date of birth, sex, phone number,
street address, city, two-letter US state, and ZIP code.

Accept information in any order and do not ask again for information already
provided. Ask a focused clarification when information is uncertain. Allow the
caller to correct any value. After collecting the required information, offer to
collect optional email, address line 2, insurance details, preferred language,
and emergency contact information. Read the complete information back and ask
for explicit confirmation.
Never invent missing information. Keep each spoken response concise and natural.
This project uses fake test data only.
""".strip()

BOOTSTRAP_SYSTEM_PROMPT = (
    CORE_SYSTEM_PROMPT
    + "\n\nThe backend save tool is not connected in this bootstrap configuration. "
    "Never claim that registration was saved. After confirmation, explain that "
    "the system is not yet able to complete the save and ask the caller to try "
    "again later."
)

TOOL_SYSTEM_PROMPT = (
    CORE_SYSTEM_PROMPT
    + "\n\nUse search_patient_by_phone after the caller provides a phone number. "
    "Use create_patient only after every required field has been collected, the "
    "complete record has been read back, and the caller explicitly confirms it. "
    "Set confirmed to true only for that explicit confirmation. Use update_patient "
    "only after the caller confirms the changes. Never claim a save or update "
    "succeeded unless the corresponding tool returns success=true. If a tool "
    "fails, apologize and explain that registration could not be completed."
)


PATIENT_PROPERTIES: dict[str, object] = {
    "first_name": {"type": "string", "description": "Confirmed patient first name."},
    "last_name": {"type": "string", "description": "Confirmed patient last name."},
    "date_of_birth": {
        "type": "string",
        "description": "Confirmed date of birth in MM/DD/YYYY format.",
    },
    "sex": {
        "type": "string",
        "enum": ["Male", "Female", "Other", "Decline to Answer"],
    },
    "phone_number": {"type": "string", "description": "Confirmed US phone number."},
    "address_line_1": {"type": "string", "description": "Confirmed street address."},
    "address_line_2": {"type": "string"},
    "city": {"type": "string"},
    "state": {"type": "string", "description": "Two-letter US state code."},
    "zip_code": {"type": "string"},
    "email": {"type": "string"},
    "insurance_provider": {"type": "string"},
    "insurance_member_id": {"type": "string"},
    "preferred_language": {"type": "string"},
    "emergency_contact_name": {"type": "string"},
    "emergency_contact_phone": {"type": "string"},
}

REQUIRED_PATIENT_FIELDS = [
    "first_name",
    "last_name",
    "date_of_birth",
    "sex",
    "phone_number",
    "address_line_1",
    "city",
    "state",
    "zip_code",
]


def build_patient_tools(server_url: str, credential_id: str) -> list[dict[str, object]]:
    server = {"url": server_url, "credentialId": credential_id}
    return [
        {
            "type": "function",
            "function": {
                "name": "search_patient_by_phone",
                "description": "Search active patient records by a caller-confirmed phone number.",
                "parameters": {
                    "type": "object",
                    "properties": {"phone_number": PATIENT_PROPERTIES["phone_number"]},
                    "required": ["phone_number"],
                    "additionalProperties": False,
                },
            },
            "server": server,
        },
        {
            "type": "function",
            "function": {
                "name": "create_patient",
                "description": (
                    "Create a patient only after reading back the complete record "
                    "and receiving explicit caller confirmation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        **PATIENT_PROPERTIES,
                        "confirmed": {
                            "type": "boolean",
                            "description": "True only after explicit caller confirmation.",
                        },
                    },
                    "required": [*REQUIRED_PATIENT_FIELDS, "confirmed"],
                    "additionalProperties": False,
                },
            },
            "server": server,
        },
        {
            "type": "function",
            "function": {
                "name": "update_patient",
                "description": "Update confirmed fields on an existing patient record.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string", "description": "Patient UUID."},
                        "fields": {
                            "type": "object",
                            "properties": PATIENT_PROPERTIES,
                            "additionalProperties": False,
                        },
                    },
                    "required": ["patient_id", "fields"],
                    "additionalProperties": False,
                },
            },
            "server": server,
        },
    ]


def build_assistant_config(
    *, tool_server_url: str | None = None, credential_id: str | None = None
) -> dict[str, object]:
    """Build the version-controlled Phase 8 Vapi assistant definition."""
    tools_enabled = tool_server_url is not None and credential_id is not None
    system_prompt = TOOL_SYSTEM_PROMPT if tools_enabled else BOOTSTRAP_SYSTEM_PROMPT
    model: dict[str, object] = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": 0.2,
        "maxTokens": 500,
        "messages": [{"role": "system", "content": system_prompt}],
    }
    if tools_enabled:
        model["tools"] = build_patient_tools(tool_server_url, credential_id)

    return {
        "name": "Patient Registration Assistant",
        "firstMessage": (
            "Hello, thank you for calling patient registration. "
            "I'll help collect your information. What is your full name?"
        ),
        "firstMessageMode": "assistant-speaks-first",
        "firstMessageInterruptionsEnabled": True,
        "model": model,
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
        "backgroundSound": "off",
        "maxDurationSeconds": 900,
        "voicemailDetection": "off",
    }
