# Repository rules

This repository has one purpose: integrating KOBIL SDK features into customer
apps through a portable skill, MCP tools and optional provider modules.

- Support Kotlin/Android, Swift/iOS and Flutter/Dart on Android, iOS, Windows and macOS.
- SDK binaries are supplied separately. Do not commit binaries, credentials,
  internal hostnames, customer identities, internal runbooks or private logs.
- Use customer-configured connections. Optional providers must not become
  prerequisites for unrelated SDK work.
- Keep dependency declaration, installation, configuration and runtime verification
  distinct. Never claim complete feature/platform coverage without evidence.
- Do not publish builds, change service accounts or send messages merely because
  a provider module was selected.
- Add tests for module selection and tool behavior. Run
  `PYTHONPATH=src python -m unittest discover -s tests -v` before committing changes.
