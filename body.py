def simplify_elevenlabs_payload(payload: dict) -> dict:
    data = payload.get("data", {})
    transcript = data.get("transcript", [])
    analysis = data.get("analysis", {})
    client_data = data.get("conversation_initiation_client_data", {})

    simplified = {
        "dynamic_variables": client_data.get("dynamic_variables", {}),
        "summary": analysis.get("transcript_summary", ""),
        "transcript": [
            {
                "role": t.get("role"),
                "message": t.get("message")
            }
            for t in transcript
            if t.get("message")
        ]
    }

    return simplified
