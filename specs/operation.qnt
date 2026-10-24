// Abstract protocol, not an implementation proof of Soodles or GitHub.
// Model checks only the state and assumptions declared below.
module OperationProtocol {
  type ProtocolState = {
    phase: str,
    authorized: bool,
    bound: bool,
    fresh: bool,
    reconciled: bool,
    effectCount: int,
    effectAuthorized: bool,
    receiptObserved: bool,
    reportedSuccess: bool,
  }

  var s: ProtocolState

  action init = s' = {
    phase: "PREPARED",
    authorized: false,
    bound: false,
    fresh: false,
    reconciled: false,
    effectCount: 0,
    effectAuthorized: false,
    receiptObserved: false,
    reportedSuccess: false,
  }

  // Approval and evidence are abstract independent oracle inputs.
  action authorize = all {
    s.phase == "PREPARED",
    s' = { ...s, authorized: true },
  }

  action bindEvidence = all {
    s.authorized,
    s' = { ...s, bound: true, fresh: true },
  }

  action advance = all {
    s.phase == "PREPARED",
    s.authorized and s.bound and s.fresh,
    s' = { ...s, phase: "CLAIMED" },
  }

  action publish = all {
    s.phase == "CLAIMED",
    s.authorized and s.bound and s.fresh,
    s.effectCount == 0,
    s' = { ...s, phase: "EXECUTING", effectCount: 1,
          effectAuthorized: s.authorized and s.bound and s.fresh },
  }

  action interrupt = all {
    s.phase == "CLAIMED",
    s' = { ...s, phase: "INTERRUPTED" },
  }

  action resume = all {
    s.phase == "INTERRUPTED",
    s.authorized and s.bound and s.fresh,
    s' = { ...s, phase: "CLAIMED" },
  }

  action markUnknown = all {
    s.phase == "CLAIMED",
    s.effectCount == 0,
    s' = { ...s, phase: "UNKNOWN" },
  }

  action advanceToExecute = all {
    s.phase == "CLAIMED",
    s.authorized and s.bound and s.fresh,
    s' = { ...s, phase: "EXECUTING" },
  }

  action markFailed = all {
    s.phase == "CLAIMED",
    s' = { ...s, phase: "FAILED" },
  }

  action reconcileNoEffect = all {
    (s.phase == "FAILED" or s.phase == "UNKNOWN"),
    s.effectCount == 0,
    s' = { ...s, reconciled: true },
  }

  action retry = all {
    (s.phase == "FAILED" or s.phase == "UNKNOWN"),
    s.reconciled and s.effectCount == 0,
    s' = { ...s, phase: if (s.phase == "UNKNOWN") "RECONCILING" else "CLAIMED", reconciled: false },
  }

  action observeEffect = all {
    s.phase == "EXECUTING",
    s.effectCount == 1,
    s' = { ...s, phase: "RECONCILED", receiptObserved: true },
  }

  action terminal = all {
    s.phase == "RECONCILED",
    s.effectCount == 1 and s.receiptObserved,
    s' = { ...s, phase: "TERMINAL", reportedSuccess: true },
  }

  action step = any {
    authorize, bindEvidence, advance, advanceToExecute, publish, interrupt, resume,
    markFailed, markUnknown, reconcileNoEffect, retry, observeEffect, terminal,
  }

  val noDuplicate = s.effectCount >= 0 and s.effectCount <= 1
  val effectHasPreconditions = s.effectCount == 0 or s.effectAuthorized
  val receiptSupported = not(s.reportedSuccess) or
    (s.phase == "TERMINAL" and s.receiptObserved and s.effectCount == 1)
  val safety = noDuplicate and effectHasPreconditions and receiptSupported
}
