"""Comprehensive test for multilingual support and verification accuracy."""
import sys
sys.path.insert(0, '.')
from app.core.llm import (
    _detect_language, _is_valid_sentence, validate_input,
    _classify_claim_type, _translate_hindi_to_english_keywords,
    _generate_search_queries_nlp,
)

passed = 0
failed = 0

def test(name, actual, expected):
    global passed, failed
    ok = actual == expected
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} => got '{actual}', expected '{expected}'")

print("=" * 60)
print("1. LANGUAGE DETECTION")
print("=" * 60)
test("English", _detect_language("Fire is a chemical reaction"), "english")
test("Hindi", _detect_language("\u0928\u0930\u0947\u0902\u0926\u094d\u0930 \u092e\u094b\u0926\u0940 \u092d\u093e\u0930\u0924 \u0915\u0947 \u092a\u094d\u0930\u0927\u093e\u0928\u092e\u0902\u0924\u094d\u0930\u0940 \u0939\u0948\u0902"), "hindi")
test("Hinglish", _detect_language("Modi India ke PM hain"), "hinglish")

print("\n" + "=" * 60)
print("2. SENTENCE VALIDATION")
print("=" * 60)
test("English valid", _is_valid_sentence("Fire is a chemical reaction"), True)
test("Hindi valid", _is_valid_sentence("\u092d\u093e\u0930\u0924 1947 \u092e\u0947\u0902 \u0906\u091c\u093c\u093e\u0926 \u0939\u0941\u0906"), True)
test("Hinglish valid", _is_valid_sentence("Modi India ke PM hain"), True)
test("Too short", _is_valid_sentence("hi"), False)

print("\n" + "=" * 60)
print("3. INPUT VALIDATION")
print("=" * 60)
v1, _ = validate_input("Fire is a chemical reaction")
test("English input", v1, True)
v2, _ = validate_input("\u0928\u0930\u0947\u0902\u0926\u094d\u0930 \u092e\u094b\u0926\u0940 \u092d\u093e\u0930\u0924 \u0915\u0947 \u092a\u094d\u0930\u0927\u093e\u0928\u092e\u0902\u0924\u094d\u0930\u0940 \u0939\u0948\u0902")
test("Hindi input", v2, True)
v3, _ = validate_input("Modi India ke PM hain")
test("Hinglish input", v3, True)

print("\n" + "=" * 60)
print("4. CLAIM CLASSIFICATION")
print("=" * 60)
test("Absurd identity EN", _classify_claim_type("Narendra Modi is Oppenheimer"), "absurd_identity")
test("Absurd identity EN 2", _classify_claim_type("Elon Musk is Albert Einstein"), "absurd_identity")
test("Factual EN", _classify_claim_type("Fire is a chemical reaction"), "factual")
test("Factual EN 2", _classify_claim_type("India gained independence in 1947"), "factual")
test("Supernatural Hindi", _classify_claim_type("\u0928\u0930\u0947\u0902\u0926\u094d\u0930 \u092e\u094b\u0926\u0940 \u0935\u093f\u0937\u094d\u0923\u0941 \u0915\u0947 \u0905\u0935\u0924\u093e\u0930 \u0939\u0948\u0902"), "supernatural")

print("\n" + "=" * 60)
print("5. HINDI TRANSLATION")
print("=" * 60)
translated = _translate_hindi_to_english_keywords("\u0928\u0930\u0947\u0902\u0926\u094d\u0930 \u092e\u094b\u0926\u0940 \u092d\u093e\u0930\u0924 \u0915\u0947 \u092a\u094d\u0930\u0927\u093e\u0928\u092e\u0902\u0924\u094d\u0930\u0940 \u0939\u0948\u0902")
print(f"  Translation: '{translated}'")
has_key_words = "Narendra" in translated and "Modi" in translated and "India" in translated
test("Hindi to English keywords", has_key_words, True)

print("\n" + "=" * 60)
print("6. SEARCH QUERIES")
print("=" * 60)
queries_en = _generate_search_queries_nlp("Fire is a chemical reaction")
print(f"  English queries: {queries_en[:3]}")
test("English queries generated", len(queries_en) >= 2, True)

queries_hi = _generate_search_queries_nlp("\u092d\u093e\u0930\u0924 1947 \u092e\u0947\u0902 \u0906\u091c\u093c\u093e\u0926 \u0939\u0941\u0906")
print(f"  Hindi queries: {queries_hi[:3]}")
test("Hindi queries generated", len(queries_hi) >= 2, True)

queries_hl = _generate_search_queries_nlp("Modi India ke PM hain")
print(f"  Hinglish queries: {queries_hl[:3]}")
test("Hinglish queries generated", len(queries_hl) >= 2, True)

print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
print("=" * 60)
