module LocalRefCASReachability {
  import LocalRefCAS.* from "./local_ref_cas"

  val rejectionUnreachable = not(s.noEffectReconciled)
  val positiveUnreachable = not(s.confirmed)
  val unknownEffectUnreachable = not(s.receipt == "UNKNOWN" and s.effectCount == 1)
}

// This action deliberately omits the expected-old condition.
// Use --step=unsafeStep; the imported normal step remains unchanged.
module LocalRefCASCanary {
  import LocalRefCAS.* from "./local_ref_cas"

  action completeUnchecked = all {
    s.receipt == "STARTED",
    not(s.gitDone),
    s' = { ...s, ref: s.target, gitDone: true, gitOutcome: "UPDATED",
      effectCount: s.effectCount + 1 },
  }

  action unsafeStep = any {
    offer, completeUnchecked, recordCompletion, loseCompletion, readback, terminalStutter,
  }
}

module LocalRefCASFalseReconciliationCanary {
  import LocalRefCAS.* from "./local_ref_cas"

  action badReadback = all {
    s.receipt == "UNKNOWN",
    s.gitDone,
    s.effectCount == 1,
    not(s.readbackSeen),
    s' = { ...s, readbackSeen: true, readbackRef: s.ref,
      noEffectReconciled: true },
  }

  action unsafeStep = any {
    offer, completeGit, recordCompletion, loseCompletion,
    readback, badReadback, terminalStutter,
  }
}
