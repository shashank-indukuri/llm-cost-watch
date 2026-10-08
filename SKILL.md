---
name: llm-cost-watch
description: Monitor OpenAI and Anthropic model releases and API pricing, compare their fit for a project's workloads, and prepare model changes for implementation when the user selects one.
---

# LLM Cost and Model Watch

Use this skill to set up and run a recurring or on-demand review of OpenAI and Anthropic API spend, model releases, pricing, and project model choices. Setup should collect project context and preferences; each review ends with concrete model choices. After the user selects a choice, update the project and run its relevant tests.

## First-run setup

If the user has not configured this skill for a project, guide them through a short setup. Ask together or in a small number of turns for:

1. The absolute path or connected repository for the codebase, and which branch/environment to review. Do not edit until the user has selected the project.
2. Which providers and billing paths they use (direct OpenAI/Anthropic API, cloud marketplace, or gateway), and whether secure credentials are already configured. Never request keys in chat.
3. Their preferred monitoring cadence and timezone, report destination, and priorities (cost, quality, latency, reliability, or a balance).

Explain that the runner needs repository access, shell/script execution, web access, and secret environment variables for account reports. Verify the configured report endpoints by running the bundled script before relying on spend data. If the user requested a recurring routine, set it up through the host's scheduler after the cadence and destination are known and the host confirms creation. If the host cannot schedule or run scripts, explain the exact missing capability and provide the manual invocation. Keep each recipient's setup, credentials, project path, and schedule local to their own host/account.

On future runs, reuse the saved setup when accessible. If the configured project path is unavailable, ask the user to connect/open it; do not substitute another repository.

## Account spend access

This workflow concerns **API platform usage and charges**, not ChatGPT Plus/Pro or Claude paid chat subscriptions. Do not claim to have read either provider account unless the run successfully retrieves its account reporting endpoint. A skill alone does not grant account access: the host or a secure integration must supply appropriately scoped credentials at run time. Never ask the user to paste a secret into chat, print credentials, or save them in the repository. If credentials, permissions, or a supported connector are missing, report that provider's actual spend as unavailable and ask for secure setup; still provide model/pricing news separately.

- **OpenAI:** use the organization Usage and Costs endpoints with an organization admin key. Retrieve `/v1/organization/costs` for provider-reported cost by daily bucket, and the relevant usage endpoint(s), grouped by `model` and project where available, to understand token/request mix. The Costs endpoint may not attribute dollar amounts to model; calculate model-level spend only as an estimate from usage and applicable rates, and reconcile it against the reported organization total. Follow pagination and label the UTC reporting window. Sources: [OpenAI Costs API](https://platform.openai.com/docs/api-reference/usage/costs), [OpenAI Usage API](https://platform.openai.com/docs/api-reference/usage).
- **Anthropic:** use the organization Admin API with an Admin API key. Prefer `GET /v1/organizations/cost_report` for the provider's reported spend and `GET /v1/organizations/usage_report/messages` for model-level token mix, including cached tokens and service tier. These are beta reporting endpoints; check current docs, permissions, data freshness, and available breakdowns on each setup/run. The analytics cost report can provide cost breakdowns where the organization has access and the required `read:analytics` scope. If cost cannot be attributed to model from the available cost report, estimate per-model cost from usage and effective rates, clearly label it, and reconcile to reported total. Source: [Anthropic Usage and Cost API](https://platform.claude.com/docs/en/api/admin-api/usage-cost).
- If API traffic is billed through AWS Bedrock, Google Vertex AI, or another gateway, provider direct-account reports may omit it. Use that billing source or gateway's account reporting when configured; do not combine it with direct-provider numbers without identifying overlap and currency.

For every scheduled or on-demand monitoring run, automatically execute [`scripts/check_account_access.py`](scripts/check_account_access.py) from the installed skill folder (for example, `python3 /path/to/llm-cost-watch/scripts/check_account_access.py --provider both --days 7`) before writing the account spend section. The script fetches read-only cost and usage reports and emits summarized JSON. Read and use that output in the report, then browse for current pricing/model releases. Credentials must already be available through the host's secure environment mechanism. Never ask the user to paste keys into chat. Follow [`SETUP.md`](SETUP.md) for setup and sharing guidance. If the script is unavailable, a key is missing, or an endpoint fails, do not claim an account check succeeded or report missing data as zero; report the failure and continue with sourced public model/pricing news where possible. A successful request proves endpoint access for that window, not coverage of every project, billing channel, or invoice item.

For every run, show actual provider-reported spend and date range first, by provider and available project/workspace/model breakdown. Then show model-level estimates only where needed, methodology, reconciliation gap, data freshness, and any excluded platform fees, credits, taxes, or commitments. Do not equate token-priced estimates to invoices or final settled billing.

## Monitoring routine

1. Establish the reporting window (since the last run, or a requested period) and project/workloads in scope. Run the bundled collector for that window, read its JSON summary, and record the returned time range/freshness and each provider's status. The script follows pagination. If only some providers are connected, identify the missing provider. If no project context is available, give account-level findings and explain what is needed for project-specific recommendations.
2. Browse current primary sources. Prefer OpenAI's model, pricing, and changelog pages and Anthropic's model, pricing, and release-note pages. Use reputable secondary reporting only to discover a possible announcement, then verify it against a primary source. Link each material claim and record publication/effective date when available and date checked.
3. Report account-spend changes against the prior run and distinguish them from token-based estimates or public list-price calculations. Report only release/pricing changes since the previous run plus relevant context. Distinguish announcement, preview, general availability, deprecation, and retirement. If no prior report/checkpoint exists, say the baseline is missing and label the run an initial snapshot.
4. Compare prices on an equivalent basis: input/output per million tokens, cached input and cache writes, batch/async, service tier, long-context, tool, and other applicable charges separately. Note currency, unit, effective date, and conditions. Never compare headline input rates alone as total cost.
5. Relate provider account usage and project usage where evidence exists: model IDs, task type, input/output/cache mix, tools and modalities, latency, reliability, context length, and quality requirements. Estimate candidate spend by applying current rates to the observed mix, adjusting for feature/tier conditions. Show assumptions and compare the estimate with available provider-reported totals. Do not claim a model is faster or better without applicable benchmark evidence.

## Report format

- **Account spend**: provider-reported actual spend for the window, currency, data freshness, and available provider/project/workspace/model breakdown; explicitly mark any provider unavailable.
- **Usage mix and reconciliation**: actual token/request usage by available dimensions, estimated per-model costs (if necessary), and difference from provider-reported totals.
- **Window checked**: period covered, check date, and whether a prior checkpoint was found.
- **Changes**: dated model launches, availability/deprecation changes, and pricing changes with direct source links.
- **Cost comparison**: comparable rates and any workload estimate, with assumptions and exclusions.
- **Project impact**: affected model IDs/config locations when inspected, compatibility or quality risks, and a recommendation (including “no change”).
- **Decision needed**: the specific model or migration options for the user to choose.
- **Sources**: official pages used, with dates checked.

Keep a compact dated checkpoint or changelog in the project only when the user asks for persistent tracking or the scheduled setup has an approved writable location. Store the last checked date, source URLs, and significant changes; do not store credentials or raw account-level usage data. Retain only aggregated spend summaries that are necessary for comparisons and approved by the user/host policy.

## Decision and implementation flow

End each review with a short decision set, including a no-change option. For each proposed model change, name the current and replacement model, affected task/config, evidence for cost and performance, expected spend impact from observed usage, compatibility changes, quality/latency uncertainty, and a rollback approach. Ask which option the user chooses. A report recommendation alone is not permission to edit.

When the user accepts an option, treat that selection as authorization to implement that specific model change and run relevant project tests. Do not make unrelated refactors or expand the selected migration. If the request to approve a broad option still leaves the target, workload, or deployment scope unclear, ask a focused question before editing.

## Code changes after selection

When the user selects a model, inspect project instructions and locate model IDs, provider adapters, configuration, tests, and deployment settings. Confirm that the chosen model is available for the relevant API/features and note required SDK/API changes. Review the working tree first and preserve existing user changes. Make the narrowest project-scoped edit, preserve a rollback path, and show the exact files and behavior affected. Do not modify secrets, deploy, change production infrastructure, or mutate provider settings as part of a model selection.

After editing, run the relevant existing local tests and report the commands and results. If quality/latency cannot be established with existing tests, identify a small evaluation the user can run; do not make billable provider API calls unless the user has authorized them. Summarize compatibility assumptions and provide verification results. Never present a price-only choice as a quality-equivalent migration without evidence; recommend a staged evaluation when quality or latency is uncertain.

## Scheduling

The skill itself does not wake up or create a timer. Configure a recurring task in a host that supports schedules, at the cadence/timezone the user selected, and invoke this skill in a context with shell execution, internet, secure credentials, and project access. Do not claim a schedule exists until the host confirms it. Each run reports and waits for the user's decision; it must not autonomously implement a model change. Once the user responds with a selection in that thread, implement that option and run relevant tests as described above.
