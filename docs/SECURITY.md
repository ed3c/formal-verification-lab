# Public-core / private-evidence security boundary

This repository is public-shareable code plus synthetic data only. It carries NO private Soodles source or trace.

- A self-contained JSON manifest SHA-256 ensures **consistency** of bytes inside the bundle relative to that manifest; it is not a digital signature, not provider authenticity, not a trustworthy timestamp.
- Freeze sensitive owner/provider records in a separate private evidence store using appropriate permissions and source/digest records. Record any actual external authentication separately; signatures are not a prerequisite to local discovery. Never commit such material here.
- The CLI reads either a frozen five-part v1 bundle or explicitly selected local JSON parts. Workspace discovery lists candidates within declared bounds. Selection disallows parent-path traversal and symlinks and never runs target code or a Provider client.
- Do not give the lab GitHub write credentials, deployment keys, issue mutation scope or task dispatch capability.
- `owner_export` data remains labelled `UNAUTHENTICATED_OFFLINE_READBACK` pending authenticated provenance implementation.
- Avoid unsafe loading (pickle), shelling out to user-provided commands, and executing checked target code in-process unless isolated.
- CrossHair may invoke analyzed Python code. Limit analysis to our pure `formal_contracts.py`; never target production handlers or I/O adapters.
- A provider's at-most-once effect cannot be inferred from an incomplete ledger. A per-operation at-most-once pass needs matching subject/key/order and complete relevant effect scope. External Owner approval is not a separate qualification requirement. A raw unbound count remains an observation.
- Private data should be redacted **before export**; sanitizing after public commit is too late.

The current Session chooses and reviews available evidence within the authorized scope. Missing authentication, mapping or lifecycle completeness affects only claims that depend on it; it is not a blanket access or engineering gate. No original Session identity is required by the Lab. Unknown facts must not be replaced with synthetic operation IDs, sequence numbers, epochs or grants.
