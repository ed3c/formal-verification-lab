// Deliberately unsafe: `quint verify` MUST find a counterexample.
// This file must never be promoted to a production protocol.
module UnsafeCanary {
  var authorized: bool
  var effected: bool

  action init = all {
    authorized' = false,
    effected' = false,
  }
  action publishUnchecked = all {
    authorized' = authorized,
    effected' = true,
  }
  action step = publishUnchecked
  val unauthorizedEffectIsImpossible = not(effected) or authorized
}
