// Symbolic OIDs and a trusted single-writer CAS, not a Native execution trace.
// UNKNOWN models loss of the completion receipt after the Git action finishes.
module LocalRefCAS {
  type CasState = {
    ref: int,
    before: int,
    target: int,
    expected: int,
    otherRef: int,
    attemptCount: int,
    gitDone: bool,
    gitOutcome: str,
    receipt: str,
    effectCount: int,
    readbackSeen: bool,
    readbackRef: int,
    noEffectReconciled: bool,
    confirmed: bool,
  }

  var s: CasState

  pure def initialState(expected: int): CasState = {
    ref: 0,
    before: 0,
    target: 1,
    expected: expected,
    otherRef: 2,
    attemptCount: 0,
    gitDone: false,
    gitOutcome: "NONE",
    receipt: "NONE",
    effectCount: 0,
    readbackSeen: false,
    readbackRef: -1,
    noEffectReconciled: false,
    confirmed: false,
  }

  action init = any {
    s' = initialState(0),
    s' = initialState(2),
  }

  action offer = all {
    s.receipt == "NONE",
    s.attemptCount == 0,
    s' = { ...s, receipt: "STARTED", attemptCount: 1 },
  }

  action completeGit = all {
    s.receipt == "STARTED",
    not(s.gitDone),
    s' = if (s.ref == s.expected)
      { ...s, ref: s.target, gitDone: true, gitOutcome: "UPDATED",
        effectCount: s.effectCount + 1 }
    else
      { ...s, gitDone: true, gitOutcome: "MISMATCH" },
  }

  action recordCompletion = all {
    s.receipt == "STARTED",
    s.gitDone,
    s' = { ...s, receipt: if (s.gitOutcome == "UPDATED")
      "COMPLETED_OK" else "COMPLETED_REJECTED" },
  }

  action loseCompletion = all {
    s.receipt == "STARTED",
    s.gitDone,
    s' = { ...s, receipt: "UNKNOWN" },
  }

  action readback = all {
    s.receipt.in(Set("COMPLETED_OK", "COMPLETED_REJECTED", "UNKNOWN")),
    not(s.readbackSeen),
    s' = { ...s, readbackSeen: true, readbackRef: s.ref,
      noEffectReconciled: s.receipt == "COMPLETED_REJECTED" and
        s.ref == s.before and s.effectCount == 0,
      confirmed: s.receipt == "COMPLETED_OK" and
        s.ref == s.target and s.effectCount == 1 },
  }

  action terminalStutter = all {
    s.readbackSeen,
    s' = s,
  }

  action step = any {
    offer, completeGit, recordCompletion, loseCompletion, readback, terminalStutter,
  }

  val atMostOneEffect = s.effectCount >= 0 and s.effectCount <= 1
  val updateRequiresMatch = s.effectCount == 0 or s.expected == s.before
  val otherRefUnchanged = s.otherRef == 2
  val rejectionPreservesRef = s.gitOutcome != "MISMATCH" or
    (s.ref == s.before and s.effectCount == 0)
  val noEffectSupported = not(s.noEffectReconciled) or
    (s.receipt == "COMPLETED_REJECTED" and s.readbackSeen and
      s.readbackRef == s.before and s.effectCount == 0)
  val confirmationSupported = not(s.confirmed) or
    (s.receipt == "COMPLETED_OK" and s.readbackSeen and
      s.readbackRef == s.target and s.effectCount == 1)
  val unknownIsNotNoEffect = s.receipt != "UNKNOWN" or not(s.noEffectReconciled)
  val atMostOneOffer = s.attemptCount >= 0 and s.attemptCount <= 1
  val safety = atMostOneEffect and updateRequiresMatch and otherRefUnchanged and
    rejectionPreservesRef and noEffectSupported and confirmationSupported and
    unknownIsNotNoEffect and atMostOneOffer
}
