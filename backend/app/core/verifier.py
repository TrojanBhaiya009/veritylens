"""
Verifier — RL-enhanced claim verification with self-critique and multi-agent debate.

Pipeline (when LLM available):
  Round 1: Initial CoT verdict (Advocate)
  Round 2: Critic challenges the verdict
  Round 3: Judge resolves with self-scored confidence
  + Reward-calibrated confidence overrides raw LLM self-report

Fallback: NLP heuristic verification with reward-model scoring.
"""

import json
import logging
import re
from .llm import ask_llm, verify_claim_local, _classify_claim_type

logger = logging.getLogger(__name__)

# ============================================================
# Prompts — Hardened Multi-Agent RL Verification
# ============================================================

ADVOCATE_PROMPT = """You are a fact-check ADVOCATE. Analyze evidence SUPPORTING this claim.
The claim may be in English, Hindi, or Hinglish.

CLAIM: "{claim}"

EVIDENCE:
{evidence}

PER-EVIDENCE ANALYSIS (mandatory):
For EACH numbered evidence item above, write ONE line:
  "[N] RELEVANT/IRRELEVANT — [what it says about the claim]"
Only mark RELEVANT if the evidence DIRECTLY addresses the specific claim — topical overlap is NOT relevance.

Then assess:
1. How many pieces of evidence DIRECTLY support this specific claim? (not just mentioning related topics)
2. Rate evidence quality 1-10 — apply these penalties:
   - If no evidence DIRECTLY quotes/states what the claim asserts → max quality 4
   - If evidence only mentions related entities/topics without confirming the claim → max quality 3
   - If sources are blogs/social media → subtract 2
3. Source credibility: Wikipedia, BBC, Nature, Reuters = high; blogs, social = low.

STRICT RULES:
- An article about topic X does NOT support a specific numerical/factual claim about X unless it states the same fact.
- Evidence mentioning both "Person A" and "Person B" does NOT prove "A is B."
- Do NOT use your own knowledge — only what's in the evidence above.

Return ONLY this JSON:
{{"position": "supported"|"weakly_supported"|"unsupported", "evidence_quality": 1-10, "key_points": ["point1", "point2"], "relevant_evidence_count": N, "reasoning": "Your per-evidence analysis followed by overall assessment"}}"""

CRITIC_PROMPT = """You are a fact-check CRITIC. Find evidence CONTRADICTING this claim and attack the Advocate's reasoning.
The claim may be in English, Hindi, or Hinglish.

CLAIM: "{claim}"

EVIDENCE:
{evidence}

ADVOCATE'S POSITION:
{advocate_position}

MANDATORY CHECKS:
1. For EACH evidence item the Advocate cited as supporting:
   - Does it ACTUALLY say what the Advocate claims it says? Quote the relevant part.
   - Is the Advocate conflating topical relevance with direct evidential support?
   - Did the Advocate cherry-pick while ignoring contradicting content in the same source?

2. Hallucination audit:
   - Did the Advocate use ANY facts/claims NOT found in the provided evidence?
   - If yes, list each hallucinated fact. This is a critical penalty.

3. Contradiction search:
   - Look for: debunking language, negation near key terms, conflicting numbers, "myth/false/wrong" patterns.
   - Quote specific contradicting phrases from the evidence.

4. Rate contradiction strength 1-10:
   - 8-10: Evidence explicitly disproves the claim
   - 5-7: Evidence casts significant doubt
   - 1-4: Only weak or indirect contradiction

IDENTITY CLAIM CHECK:
- If claim says "A IS B" (two distinct entities), the Advocate MUST have evidence explicitly stating they are the same. If not, rate contradiction_strength ≥ 8.

Return ONLY this JSON:
{{"position": "contradicted"|"weakly_contradicted"|"no_contradiction", "contradiction_strength": 1-10, "hallucinations_found": ["list of any facts Advocate used that aren't in evidence"], "key_points": ["point1", "point2"], "reasoning": "Your detailed critique with evidence quotes"}}"""

JUDGE_PROMPT = """You are the JUDGE in a fact-checking debate. Make the final verdict with a detailed, claim-specific explanation.

CLAIM: "{claim}"

EVIDENCE:
{evidence}

ADVOCATE (argues TRUE):
{advocate_analysis}

CRITIC (argues FALSE):
{critic_analysis}

JUDGING PROCESS:
1. Check each side for hallucination (using facts not in evidence) — automatic -5 credibility.
2. Check for ignored evidence — each missed strong counter-evidence is -3 credibility.
3. Check source credibility of cited evidence.
4. Determine: does the evidence DIRECTLY address the SPECIFIC claim, or only the general topic?
5. Form verdict based ONLY on provided evidence.

SELF-SCORING (be brutally honest):
Start at 10, then apply deductions:
- -3 if fewer than 3 relevant evidence items directly address the claim
- -3 if Advocate AND Critic both made strong cases (genuine ambiguity)  
- -2 if all evidence comes from similar/same source type
- -2 if verdict relies heavily on one single piece of evidence
- +2 if multiple high-credibility sources independently agree
- +1 if numerical data in evidence clearly matches/contradicts the claim

VERDICTS:
- "True" = Multiple credible sources DIRECTLY and EXPLICITLY confirm the claim
- "False" = Evidence contradicts the claim, OR the claim is factually absurd
- "Partially True" = Some aspects confirmed, others contradicted or unverifiable
- "Unverifiable" = Insufficient direct evidence, or evidence roughly balanced

CRITICAL — YOUR "detailed_analysis" IS SHOWN DIRECTLY TO THE USER:
You MUST write a 3-5 sentence analysis that is UNIQUE to this specific claim. Requirements:
- Name the specific subject (people, places, numbers, scientific concepts mentioned in the claim).
- Quote or paraphrase at least ONE specific evidence finding.
- Explain the logical connection between evidence and verdict.
- If False: state exactly WHAT is wrong and what the evidence actually says instead.
- If True: state what evidence confirms it and from which sources.
- If Partially True: state which parts are confirmed and which are not.
- NEVER write generic boilerplate — every word must be specific to THIS claim.

Return ONLY this JSON:
{{"verdict": "True"|"False"|"Partially True"|"Unverifiable", "confidence": 0-100, "self_score": 1-10, "detailed_analysis": "Your 3-5 sentence claim-specific explanation for the user", "reasoning": "Full step-by-step judgment with evidence references"}}"""

# Fallback single-pass with self-critique (when rate-limited to fewer LLM calls)
VERIFY_WITH_SELF_CRITIQUE_PROMPT = """You are an expert fact-checker. Verify this claim using a strict 4-round process.

CLAIM: "{claim}"

EVIDENCE:
{evidence}

**Round 1 — Per-Evidence Analysis:**
For EACH evidence item, write: "[N] SUPPORTS/CONTRADICTS/IRRELEVANT — [specific reason]"
Only mark SUPPORTS if the evidence DIRECTLY states or confirms what the claim asserts.
Form an initial verdict based ONLY on directly relevant evidence.

**Round 2 — Self-Critique (score yourself 1-10, start at 10):**
- -3 if you used knowledge NOT in the evidence (hallucination)
- -3 if you treated topical relevance as direct support
- -2 if you ignored any contradicting evidence
- -2 if overconfident with fewer than 3 directly relevant sources
- -1 if you ignored source credibility differences
- -3 if you treated name co-occurrence as proof of identity

**Round 3 — Revised Verdict:**
If self-score ≤ 6, you MUST reconsider and potentially change your verdict.
If self-score ≤ 4, default to "Unverifiable" unless contradiction evidence is overwhelming.

**Round 4 — Adversarial Challenge:**
Try to construct the OPPOSITE verdict using the same evidence.
- If equally compelling → "Partially True" or "Unverifiable"
- If weak opposite case → your verdict stands, boost confidence
- If opposite case reveals flaws → revise your verdict

VERDICTS:
- "True" = Multiple credible sources DIRECTLY confirm the claim
- "False" = Sources contradict the claim, OR claim is logically absurd
- "Partially True" = Some aspects confirmed, others contradicted
- "Unverifiable" = Insufficient direct evidence or balanced contradiction

YOUR "detailed_analysis" IS SHOWN TO THE USER — make it specific:
- Reference the claim's subject by name (people, places, numbers, concepts).
- Cite at least one specific evidence finding.
- Explain WHY the verdict was reached.
- NEVER use generic boilerplate. Every analysis must be unique to this claim.

Return ONLY this JSON:
{{"verdict": "True"|"False"|"Partially True"|"Unverifiable", "confidence": 0-100, "self_score": 1-10, "initial_verdict": "Round 1 verdict", "adversarial_viable": true|false, "detailed_analysis": "3-5 sentence claim-specific explanation citing evidence", "reasoning": "Full 4-round analysis"}}"""


def _format_evidence(evidence: list[dict]) -> str:
    """Format evidence list into a numbered string."""
    text = ""
    for i, e in enumerate(evidence, 1):
        title = e.get('title', 'Unknown')
        snippet = e.get('snippet', 'No content')
        url = e.get('url', '')
        text += f"\n[{i}] {title} ({url}): {snippet}\n"
    return text


def _parse_json_response(response: str) -> dict | None:
    """Extract JSON from LLM response."""
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _calibrate_confidence(
    raw_confidence: int,
    self_score: int,
    advocate_quality: int | None,
    critic_strength: int | None,
    num_evidence: int,
    rounds_consistent: bool
) -> int:
    """
    Hardened reward-calibrated confidence.
    Applies aggressive RL-style reward/penalty based on reasoning quality signals.
    Designed to prevent overconfidence and force honest uncertainty.
    """
    calibrated = raw_confidence

    # Self-score reward/penalty (most important signal — hardened)
    if self_score >= 9:
        calibrated += 5    # modest boost for very high self-awareness
    elif self_score >= 7:
        calibrated += 2
    elif self_score <= 3:
        calibrated -= 25   # LLM thinks reasoning is very weak → heavy penalty
    elif self_score <= 4:
        calibrated -= 20   # weak reasoning → significant penalty
    elif self_score <= 6:
        calibrated -= 10   # mediocre reasoning → moderate penalty

    # Multi-round consistency reward (reduced — consistency alone isn't enough)
    if rounds_consistent:
        calibrated += 3
    else:
        calibrated -= 5    # verdict flip = instability penalty

    # Evidence volume — stricter thresholds
    if num_evidence >= 6:
        calibrated += 5
    elif num_evidence >= 4:
        calibrated += 2
    elif num_evidence <= 1:
        calibrated -= 15   # nearly no evidence → heavy penalty
    elif num_evidence <= 2:
        calibrated -= 8    # thin evidence

    # Debate signal — hardened ambiguity detection
    if advocate_quality is not None and critic_strength is not None:
        if advocate_quality >= 7 and critic_strength >= 7:
            calibrated -= 18  # genuine ambiguity → big confidence drop
        elif advocate_quality >= 5 and critic_strength >= 5:
            calibrated -= 10  # mild ambiguity → moderate drop
        elif advocate_quality >= 8 and critic_strength <= 3:
            calibrated += 7   # advocate dominated clearly
        elif critic_strength >= 8 and (advocate_quality or 0) <= 3:
            calibrated += 7   # critic dominated clearly

    # Cap at 92% — no single verification should be 100% confident
    return max(5, min(92, calibrated))


async def _verify_multi_agent(claim: str, evidence: list[dict], evidence_text: str) -> dict | None:
    """
    Multi-agent debate verification (3 LLM calls).
    Returns None if any call fails (caller should fall back).
    """
    # --- Round 1: Advocate ---
    try:
        advocate_prompt = ADVOCATE_PROMPT.format(claim=claim, evidence=evidence_text)
        advocate_raw = await ask_llm(advocate_prompt, max_retries=1)
        advocate_data = _parse_json_response(advocate_raw)

        if not advocate_data:
            logger.warning("Advocate response unparseable, falling back")
            return None

        advocate_quality = int(advocate_data.get("evidence_quality", 5))
        advocate_summary = advocate_data.get("reasoning", advocate_raw[:300])
    except Exception as e:
        logger.info(f"Advocate round failed: {e}")
        return None

    # --- Round 2: Critic ---
    try:
        critic_prompt = CRITIC_PROMPT.format(
            claim=claim,
            evidence=evidence_text,
            advocate_position=json.dumps(advocate_data, indent=2)[:800]
        )
        critic_raw = await ask_llm(critic_prompt, max_retries=1)
        critic_data = _parse_json_response(critic_raw)

        if not critic_data:
            logger.warning("Critic response unparseable, falling back")
            return None

        critic_strength = int(critic_data.get("contradiction_strength", 5))
        critic_summary = critic_data.get("reasoning", critic_raw[:300])
    except Exception as e:
        logger.info(f"Critic round failed: {e}")
        return None

    # --- Round 3: Judge ---
    try:
        judge_prompt = JUDGE_PROMPT.format(
            claim=claim,
            evidence=evidence_text,
            advocate_analysis=json.dumps(advocate_data, indent=2)[:600],
            critic_analysis=json.dumps(critic_data, indent=2)[:600]
        )
        judge_raw = await ask_llm(judge_prompt, max_retries=2)
        judge_data = _parse_json_response(judge_raw)

        if not judge_data:
            logger.warning("Judge response unparseable")
            return None

        verdict = judge_data.get("verdict", "Unverifiable")
        if verdict not in ["True", "False", "Partially True", "Unverifiable"]:
            verdict = "Unverifiable"

        raw_confidence = max(0, min(100, int(judge_data.get("confidence", 50))))
        self_score = max(1, min(10, int(judge_data.get("self_score", 5))))

        calibrated = _calibrate_confidence(
            raw_confidence=raw_confidence,
            self_score=self_score,
            advocate_quality=advocate_quality,
            critic_strength=critic_strength,
            num_evidence=len(evidence),
            rounds_consistent=True  # judge is final arbiter
        )

        # Build rich reasoning — prefer detailed_analysis (claim-specific) over generic reasoning
        detailed = str(judge_data.get("detailed_analysis", "")).strip()
        full_reasoning = str(judge_data.get("reasoning", "")).strip()

        # Use detailed_analysis as primary (shown to user), append technical reasoning
        if detailed and len(detailed) > 20:
            reasoning = detailed
        elif full_reasoning:
            reasoning = full_reasoning
        else:
            reasoning = f"Verified claim about '{claim[:80]}' using multi-agent debate with {len(evidence)} evidence sources."

        # Append RL metadata for transparency
        reasoning += f"\n\n[RL Debate] Advocate: {advocate_quality}/10, Critic: {critic_strength}/10, Judge self-score: {self_score}/10. Confidence: {raw_confidence}% → {calibrated}%."

        return {
            "verdict": verdict,
            "confidence": calibrated,
            "reasoning": reasoning,
            "method": "multi-agent-debate",
            "rl_metadata": {
                "advocate_quality": advocate_quality,
                "critic_strength": critic_strength,
                "self_score": self_score,
                "raw_confidence": raw_confidence,
                "calibrated_confidence": calibrated,
            }
        }
    except Exception as e:
        logger.info(f"Judge round failed: {e}")
        return None


async def _verify_self_critique(claim: str, evidence: list[dict], evidence_text: str) -> dict | None:
    """
    Self-critique verification (single LLM call with built-in RL loop).
    Use when rate-limited and can't afford 3 calls.
    """
    try:
        prompt = VERIFY_WITH_SELF_CRITIQUE_PROMPT.format(
            claim=claim, evidence=evidence_text
        )
        response = await ask_llm(prompt, max_retries=2)
        data = _parse_json_response(response)

        if not data:
            return None

        verdict = data.get("verdict", "Unverifiable")
        if verdict not in ["True", "False", "Partially True", "Unverifiable"]:
            verdict = "Unverifiable"

        raw_confidence = max(0, min(100, int(data.get("confidence", 50))))
        self_score = max(1, min(10, int(data.get("self_score", 5))))
        initial_verdict = data.get("initial_verdict", verdict)

        rounds_consistent = (initial_verdict == verdict)

        calibrated = _calibrate_confidence(
            raw_confidence=raw_confidence,
            self_score=self_score,
            advocate_quality=None,
            critic_strength=None,
            num_evidence=len(evidence),
            rounds_consistent=rounds_consistent
        )

        # Prefer detailed_analysis (claim-specific) over generic reasoning
        detailed = str(data.get("detailed_analysis", "")).strip()
        full_reasoning = str(data.get("reasoning", "")).strip()
        adversarial_viable = data.get("adversarial_viable", False)

        if detailed and len(detailed) > 20:
            reasoning = detailed
        elif full_reasoning:
            reasoning = full_reasoning
        else:
            reasoning = f"Analyzed claim about '{claim[:80]}' against {len(evidence)} evidence sources."

        # Append RL metadata
        if initial_verdict != verdict:
            reasoning += f"\n\n[RL Self-Critique] Verdict revised from '{initial_verdict}' to '{verdict}' after 4-round analysis (score: {self_score}/10). Confidence: {raw_confidence}% → {calibrated}%."
        else:
            reasoning += f"\n\n[RL Self-Critique] Verdict confirmed after 4-round analysis (score: {self_score}/10). Confidence: {raw_confidence}% → {calibrated}%."

        if adversarial_viable:
            reasoning += " ⚠️ Adversarial challenge found viable counter-argument."
            calibrated = max(5, calibrated - 8)  # Extra penalty for viable adversarial

        return {
            "verdict": verdict,
            "confidence": calibrated,
            "reasoning": reasoning,
            "method": "self-critique",
            "rl_metadata": {
                "self_score": self_score,
                "initial_verdict": initial_verdict,
                "raw_confidence": raw_confidence,
                "calibrated_confidence": calibrated,
                "verdict_changed": initial_verdict != verdict,
                "adversarial_viable": adversarial_viable,
            }
        }
    except Exception as e:
        logger.info(f"Self-critique verification failed: {e}")
        return None


# ============================================================
# Main verification entry point
# ============================================================

async def verify_claim(claim: str, evidence: list[dict]) -> dict:
    """
    RL-enhanced claim verification pipeline.

    Strategy:
    1. Try multi-agent debate (3 LLM calls: advocate → critic → judge)
    2. If rate-limited, try self-critique (1 LLM call with built-in RL loop)
    3. If all LLM fails, use NLP fallback with reward-model scoring
    """
    if not evidence:
        return {
            "verdict": "Unverifiable",
            "confidence": 0,
            "reasoning": "No evidence could be retrieved from web sources to verify this claim.",
        }

    # Pre-LLM gate: catch absurd identity claims before burning LLM calls
    claim_type = _classify_claim_type(claim)
    if claim_type == 'absurd_identity':
        logger.info(f"Pre-LLM gate: absurd identity claim detected — '{claim}'")
        # Extract entity names from the claim for a specific explanation
        import re as _re
        claim_words = [w for w in claim.split() if len(w) > 1 and w.lower() not in {
            'is', 'are', 'was', 'were', 'hai', 'hain', 'he', 'tha', 'thi', 'the',
            'a', 'an', 'the', 'of', 'in', 'and', 'or',
        }]
        entity_a = claim_words[0] if claim_words else 'Entity A'
        entity_b = claim_words[-1] if len(claim_words) > 1 else 'Entity B'
        return {
            "verdict": "False",
            "confidence": 92,
            "reasoning": (
                f"The claim asserts that {entity_a} IS {entity_b}, equating two distinct "
                f"real-world entities. {entity_a} and {entity_b} are different individuals "
                f"with separate identities, histories, and biographies. No credible evidence "
                f"supports that they are the same person or entity. Web evidence mentioning "
                f"both names in the same context does not constitute proof of identity — "
                f"it merely indicates topical co-occurrence. This claim is factually false."
            ),
            "method": "pre-llm-identity-gate",
        }

    evidence_text = _format_evidence(evidence)

    # Strategy 1: Multi-agent debate (best quality, 3 LLM calls)
    result = await _verify_multi_agent(claim, evidence, evidence_text)
    if result:
        logger.info(f"Verified via multi-agent debate: {result['verdict']} ({result['confidence']}%)")
        return result

    # Strategy 2: Self-critique (good quality, 1 LLM call)
    result = await _verify_self_critique(claim, evidence, evidence_text)
    if result:
        logger.info(f"Verified via self-critique: {result['verdict']} ({result['confidence']}%)")
        return result

    # Strategy 3: NLP fallback with reward-model scoring
    logger.info("All LLM strategies failed — using NLP fallback with reward scoring")
    return verify_claim_local(claim, evidence)
