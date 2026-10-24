# Formal Verification RL research side branch (not Phase 1 runtime)

## Hypothesis
Verifier feedback may lower Cost per Independently Verified Task versus the existing deterministic Soodles evaluator, but only if verified improvement survives held-out tasks and a trusted external observer.

## Candidate treatments
1. Existing CLI and deterministic rules (control).
2. Agent + property-based tests (control for testing increase).
3. Agent + counterexample-guided formal feedback (inference-only treatment).
4. Optional proof-guided fine-tuning / RLVR (later, dependent on 3 showing gain).

## Reward decomposition
Keep hard refusals outside the scalar reward. If operation identity, authorization or evidence provenance is violated, reject regardless of score. Do not reward proofs of weaker specifications.

For valid admitted tasks, measure *verified successful outcomes* and actual resource cost. A possible research score is `verified_outcome - lambda * observed_cost - mu * false_acceptance`, but weights remain hypotheses until an experiment and decision owner define them. Process-level feedback can point to the first invalid transition; it is not automatically evidence of successful external effect.

## Training dataset safety
- Use synthetic or explicitly licensed/authorized traces. Keep private traces in private storage.
- Freeze specification and independent reward oracle before training. Never allow the agent to edit its own oracle and gain a passing reward.
- Use paired held-out tasks with identical provider environment, task semantics and admitted scope.
- Preserve specification-drift controls, false acceptance controls and uncertainty as separate metrics.
- Compare baseline, enhanced verifier and RL treatment on Cost per Verified Task, hard gate violations, recall on planted controls and unknown rate.

## Sources for follow-up
- https://github.com/leanprover/lean4
- https://github.com/quint-co/quint
- https://github.com/apalache-mc/apalache
- https://github.com/pschanely/CrossHair
- https://github.com/HypothesisWorks/hypothesis

None of these sources constitutes a claim that RL training ran in this repository.
