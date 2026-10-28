module P3Induction {
  import OperationProtocol.* from "../../../specs/operation"

  pure val phases = Set(
    "PREPARED", "CLAIMED", "EXECUTING", "INTERRUPTED", "UNKNOWN",
    "FAILED", "RECONCILING", "RECONCILED", "TERMINAL"
  )
  pure val booleans = Set(false, true)
  pure val states = tuples(
    phases, booleans, booleans, booleans, booleans,
    Set(0, 1), booleans, booleans, booleans
  ).map(t => {
    phase: t._1,
    authorized: t._2,
    bound: t._3,
    fresh: t._4,
    reconciled: t._5,
    effectCount: t._6,
    effectAuthorized: t._7,
    receiptObserved: t._8,
    reportedSuccess: t._9,
  })

  val TypeOK = s.in(states)
  val IndInv = TypeOK and safety
}
