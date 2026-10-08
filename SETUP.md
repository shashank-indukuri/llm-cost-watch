# Account access and sharing

This folder is the shareable skill package. The skill contains no credentials. Each person must connect their own provider accounts in the host where they run it; a copy of the folder does not copy account access or a recurring schedule.

## Start setup in the assistant

After installing/enabling the skill, start a conversation in the project you want monitored and say:

> Use $llm-cost-watch to set up recurring API cost and model monitoring for this project. Ask me for the repository location, providers/billing paths, cadence and timezone, report destination, and whether cost, quality, or latency matters most. Check account access without asking me to paste secrets. Each report should end with specific model choices; wait for my choice, then update only the selected model configuration and run the relevant project tests.

The assistant should ask for project/access preferences first. Put secrets in the runner's secure environment, never in this setup conversation. The report-and-decision step is separate from editing: a recommendation alone must not change code.

## Verify API report access

1. Create provider keys with the least access needed for organization reporting. The checks below only use read-only GET requests. OpenAI organization cost/usage reports require an organization admin key. Anthropic organization reports require an Admin API key; organization analytics breakdowns may additionally require plan eligibility and `read:analytics` scope.
2. Set the keys through the host's secure secret or environment-variable facility. Use these variable names:
   - `OPENAI_ADMIN_KEY`
   - `ANTHROPIC_ADMIN_KEY`
3. Run the read-only collector from this folder:

   ```sh
   python3 scripts/check_account_access.py --provider both --days 7
   ```

   Or check one provider and a specific UTC date:

   ```sh
   python3 scripts/check_account_access.py --provider openai --days 7 --end-date 2026-09-28
   python3 scripts/check_account_access.py --provider anthropic --days 7 --end-date 2026-09-28
   ```

The default window is seven UTC days ending three days ago, to reduce false zeroes from reporting delays. The script outputs JSON summaries with provider-reported cost totals, available model/line-item splits, token usage by model, and provider status. Treat that output as sensitive account data. It never prints API keys or raw API response bodies. If the provider reports an empty window, rerun for a date range with known API activity. `--days` supports up to 180 days for OpenAI or 31 days for Anthropic; for `both`, it is limited to 31 days.

If a key is missing, the provider will be marked `skipped`. A provider failure is marked `error`; a cost success with usage failure is `partial`. The process exits nonzero if every provider is skipped or any provider fails, so schedulers can surface a problem rather than silently treating it as zero spend. A 401/403 usually means the key type, organization, or role/scope is insufficient; 404/other errors can indicate endpoint availability or account entitlement. Check the current official API reference before changing endpoint details.

Do not paste credentials into ChatGPT/Claude conversations, commit them, put them in `.env` files included in the package, or share screenshots/logs containing secret values. Prefer a secrets manager or the host's protected environment configuration. Rotate a key if it is accidentally exposed.

## Schedule and reuse

Configure a recurring task in the chosen assistant host to invoke the skill in a context that has both:

- Secure access to the relevant read-only reporting credentials as `OPENAI_ADMIN_KEY` and/or `ANTHROPIC_ADMIN_KEY`, plus internet/API and local script execution access.
- Access to the project repository if you want project-specific model recommendations.

On each invocation the skill should run `python3 /path/to/llm-cost-watch/scripts/check_account_access.py --provider both --days 7`, use its JSON output for the spend/usage section, and then check official current model/pricing/release sources. Tell the schedule its cadence, project/repository, and where reports should be delivered. Run the collector once manually before enabling recurring runs. Schedules and secret connections are host/account-specific and must be created again by each recipient.

## Cost data boundaries

- OpenAI's organization Costs report is provider-reported spend; pair it with Usage reports for model/token mix. Cost may not be attributable to a model in the returned cost data, in which case model-level dollars are estimates, not reported invoice charges.
- Anthropic's organization Cost report can include model/line-item breakdowns; pair it with the Messages Usage report. Use any available detailed cost breakdown and mark unavailable dimensions rather than infer them. Analytics endpoints may require additional eligibility and scope. Label totals, estimates, date range, currency, and data freshness.
- Provider APIs may omit usage billed through cloud marketplaces, gateways, credits, adjustments, taxes, or invoices. Report those separately and do not add overlapping data twice.

Official references:

- [OpenAI Costs](https://platform.openai.com/docs/api-reference/usage/costs)
- [OpenAI Usage](https://platform.openai.com/docs/api-reference/usage)
- [Anthropic Usage and Cost Admin API](https://platform.claude.com/docs/en/api/admin-api/usage-cost)
- [Anthropic Analytics Cost Report](https://platform.claude.com/docs/en/api/http/beta/organization/analytics/cost_report)
