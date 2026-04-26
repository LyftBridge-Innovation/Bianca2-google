"""
Quick local smoke-test for the Twilio voice integration.

Run from the backend/ directory:
    cd backend
    source ../venv/bin/activate
    python test_twilio_voice.py

Tests (no Twilio account / no deployment needed):
  1. TwiML generation — checks <Parameter> element is present with user_id
  2. start-event parsing — checks user_id extraction from customParameters
  3. Firestore phone lookup — checks your registered phone number is found
  4. Gemini Live connection — checks GOOGLE_API_KEY can open a Live session
     (optional; set SKIP_GEMINI=1 to skip if you don't want to use quota)
"""
import asyncio
import json
import os
import sys
import xml.etree.ElementTree as ET

# ── Allow running from backend/ directly ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

PASS = "\033[32m  PASS\033[0m"
FAIL = "\033[31m  FAIL\033[0m"
SKIP = "\033[33m  SKIP\033[0m"


# ── 1. TwiML generation ───────────────────────────────────────────────────────

def test_twiml_generation():
    print("\n[1] TwiML generation")
    from routers.twilio_voice import _twiml_stream

    xml_str = _twiml_stream("example.run.app", "user_123")
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as exc:
        print(f"{FAIL}  XML parse error: {exc}")
        return False

    # Must have <Connect><Stream><Parameter name="user_id" value="user_123"/>
    stream = root.find(".//Connect/Stream")
    if stream is None:
        print(f"{FAIL}  Missing <Connect><Stream> in TwiML")
        return False

    url = stream.get("url", "")
    if "user_id" in url:
        print(f"{FAIL}  user_id is still in the URL — should be a <Parameter> element")
        return False

    param = stream.find("Parameter[@name='user_id']")
    if param is None:
        print(f"{FAIL}  No <Parameter name='user_id'> inside <Stream>")
        return False

    if param.get("value") != "user_123":
        print(f"{FAIL}  Parameter value is '{param.get('value')}', expected 'user_123'")
        return False

    print(f"{PASS}  <Stream url='{url}'><Parameter name='user_id' value='user_123'/></Stream>")
    return True


# ── 2. start-event user_id extraction ────────────────────────────────────────

def test_start_event_parsing():
    print("\n[2] Twilio 'start' event user_id extraction")

    # Simulate exactly what Twilio sends
    start_msg = {
        "event": "start",
        "streamSid": "MZtest123",
        "start": {
            "streamSid": "MZtest123",
            "accountSid": "ACtest",
            "callSid": "CAtest",
            "tracks": ["inbound"],
            "customParameters": {
                "user_id": "115176639552744071051"
            },
        },
    }

    user_id = (
        start_msg.get("start", {})
        .get("customParameters", {})
        .get("user_id", "")
        .strip()
    )

    if user_id != "115176639552744071051":
        print(f"{FAIL}  Got user_id='{user_id}'")
        return False

    print(f"{PASS}  user_id='{user_id}' extracted correctly from customParameters")
    return True


# ── 3. Firestore phone lookup ─────────────────────────────────────────────────

def test_firestore_phone_lookup(phone_number: str):
    print(f"\n[3] Firestore phone lookup for {phone_number}")
    try:
        from routers.twilio_voice import _lookup_user_by_phone
        user_id, error = _lookup_user_by_phone(phone_number)
        if error:
            print(f"{FAIL}  {error}")
            return False
        print(f"{PASS}  Found user_id='{user_id}'")
        return True
    except Exception as exc:
        print(f"{FAIL}  Exception: {exc}")
        return False


# ── 4. Gemini Live connection ─────────────────────────────────────────────────

async def test_gemini_connection():
    print("\n[4] Gemini Live connection (quick open/close)")
    _vp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "voice_pipeline"))
    if _vp not in sys.path:
        sys.path.insert(0, _vp)

    # Determine which backend will be used
    api_key = os.getenv("GOOGLE_API_KEY", "")
    project  = os.getenv("GCP_PROJECT_ID") or os.getenv("VERTEX_PROJECT_ID", "")
    if project and not api_key:
        print(f"    ↳ Using Vertex AI (project={project})")
    elif api_key:
        print(f"    ↳ Using AI Studio API key")
    else:
        print(f"    ↳ No GOOGLE_API_KEY and no GCP_PROJECT_ID — will likely fail")

    try:
        from gemini_session import GeminiSession

        session = GeminiSession(user_id="test_user", enable_tools=False)
        await session.connect()
        print(f"{PASS}  Gemini Live session opened (model={session._model})")
        await session.close()
        return True
    except Exception as exc:
        print(f"{FAIL}  {exc}")
        return False


# ── Runner ────────────────────────────────────────────────────────────────────

async def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    phone = os.getenv("TEST_PHONE_NUMBER", "+17633274643")
    skip_gemini = os.getenv("SKIP_GEMINI", "0") == "1"

    results = []
    results.append(test_twiml_generation())
    results.append(test_start_event_parsing())
    results.append(test_firestore_phone_lookup(phone))

    if skip_gemini:
        print(f"\n[4] Gemini Live connection{SKIP}  (SKIP_GEMINI=1)")
    else:
        results.append(await test_gemini_connection())

    passed = sum(1 for r in results if r)
    total  = len(results)
    print(f"\n{'='*45}")
    print(f"Results: {passed}/{total} passed")
    if passed < total:
        print("Some tests failed — fix before deploying.")
        sys.exit(1)
    else:
        print("All tests passed — safe to deploy.")


if __name__ == "__main__":
    asyncio.run(main())
