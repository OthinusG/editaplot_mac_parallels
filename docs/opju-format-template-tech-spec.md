# OPJU Format Template

## Outcome

Allow an approved render to accept one `.opju` file as a read-only graph-format source. After the
normal renderer saves its editable project, copy all format properties from the template's active
graph page (or its first graph page) to the rendered graph, then save and export the final artifacts
again.

## Contract

- CLI: `editaplot.cmd render <plan> --format-template-opju <template.opju>`.
- The CLI records the template SHA-256 in the worker command; the worker verifies it before Origin.
- The source `.opju` is never modified or copied into the delivery directory.
- Origin's built-in page-level `Copy Format: All` and `Paste Format` actions are the transport. The
  target project is reopened, formatted, saved, and exported before artifact verification.
- The final verification report records the template digest and successful application without a
  local template path.

## Acceptance

- Missing, non-file, non-OPJU, or changed templates fail before format application.
- All existing renders behave unchanged when the option is absent.
- A successful formatted render leaves final OPJU/PNG/PDF/TIF artifacts and reports the applied
  template digest.
- Windows Origin smoke testing is required before claiming live compatibility.
