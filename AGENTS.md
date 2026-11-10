# Fork contribution rules

Preserve the upstream architecture and existing behavior. Keep personal HA
packaging separate from upstream contribution branches.

New UI text must support Czech, English and Swedish together. Retain Swedish UI
source keys and add English/Czech catalog entries using the existing translator.
Use English for new non-localized background diagnostics, technical logs, code
comments, commit/PR messages and release notes. Do not rewrite upstream translated
logs or historical release notes just to change their language.

See [language policy and workflow](docs/fork-workflow.md). Record new fork release
notes in English in `ha-addon/smartbox/CHANGELOG.md`.
