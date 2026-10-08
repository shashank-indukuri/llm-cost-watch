# LLM Cost Watch

A reusable assistant skill for monitoring OpenAI and Anthropic API spend, tracking model releases and prices, and proposing project model updates for your approval.

## What it does

- Collects provider-reported API cost and usage summaries through read-only report endpoints.
- Compares usage with current model pricing and release information.
- Asks for the project and monitoring preferences during setup.
- Presents model-change options and waits for your choice before editing a project.
- Runs relevant existing project tests after you approve a model change.

## Start here

Read [SETUP.md](SETUP.md) for installation, secure account access, manual verification, and a starter prompt. The assistant host must support the capabilities you need: recurring tasks, script execution, internet access, secure environment variables, and access to the target repository.

The repository contains no provider credentials. Each user configures their own API access and schedule. Never commit API keys or account reports here. Public model pricing/release research can still run if account report access is unavailable, but account spend must then be marked unavailable.

See [SKILL.md](SKILL.md) for the full workflow and approval boundaries.
