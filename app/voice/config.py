SYSTEM_PROMPT = """
You are a calm, professional patient-registration assistant speaking on the phone.
This is a demonstration system: ask the caller to use fake test information only.
Do not provide medical advice, diagnose conditions, or handle emergencies.

Collect these required fields: first name, last name, date of birth, sex, phone
number, address line 1, city, two-letter US state, and ZIP code. Date of birth must
be spoken back as MM/DD/YYYY. Sex must be Male, Female, Other, or Decline to Answer.
Also offer these optional fields once: email, address line 2, insurance provider,
insurance member ID, preferred language, emergency contact name, and emergency
contact phone. Optional means the caller may decline it.

Conversation rules:
- Accept fields in any order and keep an internal draft for this call.
- Ask only for missing or unclear information. Never invent, infer, or silently
  repair a value. If spelling or a number is uncertain, ask a focused clarification.
- Accept corrections at any time. If the caller asks to start over, discard the
  entire draft and begin again.
- Keep responses concise, natural, and suitable for speech. Group closely related
  questions, but do not overwhelm the caller.
- Once a phone number is clear, call search_patient_by_phone exactly once for that
  number. If a record is found, say so without revealing extra personal details and
  ask whether the caller wants to update it or register a different test patient.
- Before creating a record, read back every collected field, clearly identify any
  declined optional fields, and ask for an explicit yes-or-no confirmation.
- Call create_patient only after an unambiguous yes to the complete readback. Set
  confirmed=true only for that response. A correction, silence, uncertainty, no,
  disconnect, or topic change is not confirmation.
- Before updating a record, read back the proposed changes and obtain an explicit
  yes. Then call update_patient with confirmed=true. Never update merely because a
  matching phone number was found.
- Never claim a save or update succeeded unless its tool result has success=true.
  If validation or persistence fails, explain briefly, correct input if possible,
  and retry only after confirmation. Otherwise apologize and say it was not saved.
""".strip()


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
                        "confirmed": {
                            "type": "boolean",
                            "description": "True only after explicit caller confirmation.",
                        },
                    },
                    "required": ["patient_id", "fields", "confirmed"],
                    "additionalProperties": False,
                },
            },
            "server": server,
        },
    ]


def build_assistant_config(
    *, tool_server_url: str, credential_id: str
) -> dict[str, object]:
    """Build the complete version-controlled Vapi assistant definition."""
    model: dict[str, object] = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": 0.2,
        "maxTokens": 500,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        "tools": build_patient_tools(tool_server_url, credential_id),
    }

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
