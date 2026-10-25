// Slots characterize the proof domain; they are not additional protocol state.
module LocalRefCASInduction {
  import LocalRefCAS.* from "./local_ref_cas"

  pure def stateFor(expected: int, slot: int): CasState = {
    ref: if (slot >= 2 and expected == 0) 1 else 0,
    before: 0,
    target: 1,
    expected: expected,
    otherRef: 2,
    attemptCount: if (slot == 0) 0 else 1,
    gitDone: slot >= 2,
    gitOutcome: if (slot < 2) "NONE"
      else if (expected == 0) "UPDATED" else "MISMATCH",
    receipt: if (slot == 0) "NONE"
      else if (slot == 1 or slot == 2) "STARTED"
      else if (slot == 4 or slot == 6) "UNKNOWN"
      else if (expected == 0) "COMPLETED_OK" else "COMPLETED_REJECTED",
    effectCount: if (slot >= 2 and expected == 0) 1 else 0,
    readbackSeen: slot >= 5,
    readbackRef: if (slot >= 5) (if (expected == 0) 1 else 0) else -1,
    noEffectReconciled: slot == 5 and expected == 2,
    confirmed: slot == 5 and expected == 0,
  }

  pure val consistentStates = tuples(
    Set(0, 2), Set(0, 1, 2, 3, 4, 5, 6)
  ).map(t => stateFor(t._1, t._2))

  pure val candidateCountIs14 = consistentStates.size() == 14
  val proofTarget = safety and candidateCountIs14
  val IndInv = s.in(consistentStates)

  pure val missingInitialStates = consistentStates.filter(
    candidate => candidate != stateFor(2, 0)
  )
  val MissingInitialInv = s.in(missingInitialStates)

  pure val offeredMatching = stateFor(0, 1)
  pure val prematureEffect = { ...offeredMatching, effectCount: 1 }
  val WeakInv = s.in(consistentStates.union(Set(prematureEffect)))

  pure val unknownMatchingReadback = stateFor(0, 6)
  pure val falseNoEffect = {
    ...unknownMatchingReadback, noEffectReconciled: true,
  }
  val BadProjectionInv = s.in(consistentStates.union(Set(falseNoEffect)))
}
