# Launch checklist (default)

The default checklist `launch-gate` walks when the project ships none of its own.
A project's `docs/LAUNCH-CHECKLIST.md`, when it exists, overrides this file phase for phase.

Provider names are deliberately absent. Each phase says what must be true, not which
vendor makes it true. Record the vendor you used in the verbatim-record block.

## Phase 1: Domain

- [ ] Domain bought and the registrar account is one you control.
- [ ] Nameservers point at the DNS provider you intend to use.
- [ ] Apex and `www` both resolve. Record the A/CNAME targets verbatim.
- [ ] Verify: `dig +short <domain>` and `dig +short www.<domain>` return the expected targets.

## Phase 2: Email routing

- [ ] MX records set for the mail provider. Record each record verbatim.
- [ ] A test message to `hello@<domain>` (or the chosen address) arrives.
- [ ] Verify: `dig +short MX <domain>`.

## Phase 3: Email authentication

- [ ] SPF TXT record published. Record the string verbatim.
- [ ] DKIM record published with the provider's selector.
- [ ] DMARC TXT record published at `_dmarc.<domain>`.
- [ ] Verify: `dig +short TXT <domain>` and `dig +short TXT _dmarc.<domain>`.

## Phase 4: Email send-as

- [ ] Sending identity configured in the mail client.
- [ ] A real send and a real reply both work. No command proves this. A successful
      round trip, confirmed by the human, closes the item.

## Phase 5: Analytics

- [ ] Analytics installed on every page, not just the home page.
- [ ] A real pageview appears in the dashboard.
- [ ] Verify: read the pageview count through the hosting or analytics provider's CLI,
      API, or dashboard. A screenshot or pasted dashboard output is accepted evidence.

## Phase 6: Hosting and deploy

- [ ] Git repository linked to the hosting project.
- [ ] Production branch set, and a deploy from it succeeded.
- [ ] Custom domain attached, HTTPS certificate issued.
- [ ] Verify: `curl -sI https://<domain>` returns 200 and a valid certificate.
      Deployment state comes from the hosting provider's CLI, API, or dashboard.
      A screenshot or pasted CLI output is accepted evidence.

## Phase 7: Keep-alive (skip if not applicable)

- [ ] If any service auto-pauses on a free tier, a scheduled ping keeps it warm.
- [ ] Skip with a one-line reason when no such service is used.

## Phase 8: Cross-sell and distribution

- [ ] Links from sibling projects or properties are live.
- [ ] Launch announcement drafted. Sending it stays a human decision.

## Phase 9: Documentation

- [ ] Project status file updated with the live URL and launch date.
- [ ] `docs/DECISIONS.md` records the DNS, email, analytics, and hosting choices.
- [ ] Portfolio or dashboard row updated, if one exists.

## Phase 10: Verification

Run every check again, for real, and paste the output.

- [ ] `dig +short <domain>`
- [ ] `dig +short MX <domain>`
- [ ] `dig +short TXT <domain>` (SPF)
- [ ] `dig +short TXT _dmarc.<domain>`
- [ ] `curl -sI https://<domain>` returns 200
- [ ] `curl -sI https://www.<domain>` redirects or returns 200
- [ ] Analytics shows at least one real pageview (provider CLI, API, or dashboard output)
- [ ] One real email send and one real reply confirmed

## Verbatim record

Copy each value exactly as the provider gave it. A retyped TXT record is a silent failure.

```
Domain:
Registrar:
DNS provider:
Nameservers:
A / CNAME records:
MX records:
SPF:
DKIM selector + record:
DMARC:
Hosting provider + project:
Analytics provider + property ID:
Launch date:
```
