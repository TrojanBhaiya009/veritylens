"""Test identity detection with all claim variants."""
import sys
sys.path.insert(0, '.')
from app.core.llm import _classify_claim_type

tests = [
    # MUST be detected as absurd_identity
    ("Narendra modi oppenheimer hain", "absurd_identity", "Hinglish SOV lowercase"),
    ("narendra modi is oppenheimer", "absurd_identity", "English lowercase"),
    ("Narendra Modi is Oppenheimer", "absurd_identity", "English proper case"),
    ("Elon Musk is Albert Einstein", "absurd_identity", "English two names each"),
    ("Modi oppenheimer hai", "absurd_identity", "Hinglish SOV short"),
    
    # MUST NOT be detected as absurd_identity
    ("Fire is a chemical reaction", "factual", "Factual with 'a'"),
    ("India gained independence in 1947", "factual", "Factual historical"),
    ("Narendra Modi is the prime minister of India", "factual", "Legitimate title"),
    ("Cillian Murphy played Oppenheimer", "factual", "Role context"),
]

passed = 0
failed = 0
for claim, expected, desc in tests:
    actual = _classify_claim_type(claim)
    ok = actual == expected
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  {status}  [{desc}] {claim!r} => {actual} (expected: {expected})")

print(f"\nResults: {passed}/{passed+failed} passed")
