BOOTSTRAP_SYSTEM_PROMPT = """
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

The backend save tool is not connected in this bootstrap configuration. Never
claim that registration was saved. After confirmation, explain that the system
is not yet able to complete the save and ask the caller to try again later.
Never invent missing information. Keep each spoken response concise and natural.
This project uses fake test data only.
""".strip()


def build_assistant_config() -> dict[str, object]:
    """Build the version-controlled Phase 8 Vapi assistant definition."""
    return {
        "name": "Patient Registration Assistant",
        "firstMessage": (
            "Hello, thank you for calling patient registration. "
            "I'll help collect your information. What is your full name?"
        ),
        "firstMessageMode": "assistant-speaks-first",
        "firstMessageInterruptionsEnabled": True,
        "model": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0.2,
            "maxTokens": 500,
            "messages": [
                {
                    "role": "system",
                    "content": BOOTSTRAP_SYSTEM_PROMPT,
                }
            ],
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
        "backgroundSound": "off",
        "maxDurationSeconds": 900,
        "voicemailDetection": "off",
    }
