"""Test pipeline with improved confidence."""
import httpx
import json

test_cases = [
    "Fire is a chemical reaction.",
    "Narendra Modi is avatar of Vishnu. The Earth revolves around the Sun. India gained independence in 1947.",
    "The Great Wall of China is visible from space with the naked eye. The human body has 206 bones. Water boils at 100 degrees Celsius.",
]

for text in test_cases:
    print(f"\n{'='*60}")
    print(f"INPUT: {text[:80]}...")
    print('='*60)

    r = httpx.post(
        "http://localhost:8000/api/analyze",
        json={"text": text, "url": ""},
        timeout=120,
    )

    for line in r.text.split("\n"):
        if line.startswith("data: ") and "overall_score" in line:
            data = json.loads(line[6:])
            print(f"Overall Score: {data['overall_score']}")
            ai = data.get("ai_detection", {})
            print(f"AI Detection: {ai.get('ai_probability', 'N/A')}%")
            for c in data["claims"]:
                print(f"  [{c['verdict']}] ({c['confidence']}%) {c['claim'][:80]}")
                print(f"    => {c['reasoning'][:130]}")
            break
    print()
