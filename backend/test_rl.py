"""Quick test of the RL-enhanced pipeline."""
import httpx
import json

r = httpx.post(
    "http://localhost:8000/api/analyze",
    json={"text": "Fire is a chemical reaction. The Great Wall of China is visible from space.", "url": ""},
    timeout=120,
)

for line in r.text.strip().split("\n"):
    if not line.startswith("data:"):
        continue
    raw = line[5:].strip()
    if not raw:
        continue
    try:
        data = json.loads(raw)
    except:
        continue

    if "verdict" in data and "claim" in data:
        print(f"\n[{data['verdict']}] ({data['confidence']}%) — {data.get('rl_method', 'n/a')}")
        print(f"  Claim: {data['claim']}")
        reasoning = data.get("reasoning", "")
        # Print last 200 chars which contain RL metadata
        if "[RL" in reasoning:
            rl_part = reasoning[reasoning.index("[RL"):]
            print(f"  RL: {rl_part[:200]}")
        else:
            print(f"  Reasoning: {reasoning[:200]}")
    elif "stage" in data and data.get("stage") == "complete":
        print(f"\n✔ Analysis complete!")

print("\nDone.")
