# Codex task template

## Basic rules
- Work in `UTR_USB_Python_CodeX`, not the original `UTR_USB_Python` repository.
- Keep PowerShell confirmation commands on the Codex side by default.
- Do not ask the user to repeatedly paste `git status`, branch checks, `scripts/dev_check.ps1`, or `scripts/git_preflight.ps1`.
- If an operation needs user approval, group the approval request into one clear confirmation when possible.

## Human approval boundary
- Do not run USB hardware communication unless the user explicitly approves it.
- Do not run `src/utr_usb_sample.py` unless the user explicitly approves it.
- Do not edit `src/utr_usb_sample.py` unless the task explicitly asks for that file.
- Do not run `git commit`, `git push`, create a PR, or merge a PR unless the user explicitly approves it.

## Expected checks
- Prefer `scripts/dev_check.ps1` for local development checks.
- Prefer `scripts/git_preflight.ps1` before publishing work.
- Keep PR creation and merge as manual human actions.
