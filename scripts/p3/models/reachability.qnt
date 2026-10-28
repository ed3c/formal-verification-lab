module P3Reachability {
  import OperationProtocol.* from "../../../specs/operation"

  val terminalUnreachable = s.phase != "TERMINAL"
  val reconciliationUnreachable = s.phase != "RECONCILING"
}
