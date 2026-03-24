# 10-Minute Presentation Outline

## 1. Problem (1 min)

- Misinformation and LLM hallucinations are increasing.
- Manual fact-checking does not scale.
- Enterprises need explainable and auditable automated verification.

## 2. Solution Walkthrough (2 min)

- Input: text or URL.
- Pipeline status: Extracting -> Searching -> Verifying.
- Output: per-claim verdict, confidence, rationale, citations, conflict flag.

## 3. Live Demo Cases (5 min)

### Case A: High Accuracy Content

- Use a reputable factual report/news summary.
- Show mostly True verdicts.

### Case B: Mixed Accuracy Content

- Use content with a blend of correct and incorrect statements.
- Highlight Partially True and False verdicts.

### Case C: Conflicting Evidence

- Use a controversial or rapidly changing topic.
- Show conflicting claims list and explain ambiguity handling.

## 4. Bonus Capability (1 min)

- Show AI-generated probability score.
- Clarify that this is probabilistic and not absolute proof.

## 5. Innovation & Next Steps (1 min)

- Add source trust weighting and temporal validity scoring.
- Add caching/rate-limit resilience.
- Extend to image/audio deepfake classifiers.
