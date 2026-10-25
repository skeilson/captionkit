# Security Policy

## Supported versions

CaptionKit is early-stage. Security fixes are made on the `main` branch only.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report them privately through GitHub instead: go to the **Security** tab of
this repository and choose **Report a vulnerability**. Include what you found,
how to reproduce it, and what impact you think it has.

You can expect an acknowledgement within a week. Once a fix is ready, the
report will be credited in the release notes unless you'd prefer otherwise.

## Security and privacy design

- Audio stays on the device. Speech is transcribed locally. CaptionKit
  makes no network requests except downloading speech models the first time
  they're used (from Hugging Face).
- Transcripts are written to disk at the path set in `config.yaml`. Treat
  them as sensitive meeting records.
- Configuration is parsed with `yaml.safe_load`, which cannot execute code
  embedded in a config file.

## Automated checks

Every push and pull request runs:

- **Ruff** for linting
- **Bandit** for Python security issues
- **pip-audit** against known vulnerabilities in pinned dependencies (also weekly)
- **CodeQL** code scanning
- **Dependabot** alerts and update pull requests
- **Secret scanning** with push protection
