"""Test identity claim detection — should return FALSE for absurd identity claims."""
import httpx
import json

test_cases = [
    # (input_text, expected_verdict, description)
    ("Narendra Modi is Oppenheimer", "False", "Absurd identity: two distinct real people"),
    ("Elon Musk is Albert Einstein", "False", "Absurd identity: two distinct real people"),
    ("India gained independence in 1947", "True", "Legitimate factual claim"),
    ("Fire is a chemical reaction", "True", "Legitimate factual claim"),
]

print("=" * 70)
print("IDENTITY CLAIM DETECTION TEST")
print("=" * 70)

passed = 0
failed = 0

for text, expected, desc in test_cases:
    print(f"\n{'─'*60}")
    print(f"CLAIM:    {text}")
    print(f"EXPECTED: {expected}")
    print(f"DESC:     {desc}")

    try:
        r = httpx.post(
            "http://localhost:8000/api/analyze",
            json={"text": text, "url": ""},
            timeout=120,
        )

        verdict_found = False
        for line in r.text.split("\n"):
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            if "verdict" in data and "claim" in data:
                actual = data["verdict"]
                conf = data.get("confidence", "?")
                method = data.get("rl_method", "n/a")
                reasoning = data.get("reasoning", "")[:200]

                status = "✅ PASS" if actual == expected else "❌ FAIL"
                if actual != expected:
                    failed += 1
                else:
                    passed += 1

                print(f"ACTUAL:   {actual} ({conf}%) via {method}")
                print(f"STATUS:   {status}")
                print(f"REASON:   {reasoning}")
                verdict_found = True

        if not verdict_found:
            print("STATUS:   ⚠️  No verdict found in response")
            failed += 1

    except Exception as e:
        print(f"STATUS:   ❌ ERROR: {e}")
        failed += 1

print(f"\n{'='*70}")
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 70)
