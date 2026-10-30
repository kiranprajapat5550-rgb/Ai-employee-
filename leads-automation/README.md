# Leads Automation (Consent-Based)

Approval-first follow-up project. Contacts only people who explicitly opted in to the relevant channel.

## Safety defaults
- Dry-run is enabled by default.
- Live sending requires both `DRY_RUN=0` and `SEND_ENABLED=true`.
- Each channel requires its own consent flag in `leads.csv`.
- GitHub Actions is manual-only; no schedule is configured.
- Store credentials in secure GitHub Actions Secrets; never commit them.

## Files
- `outreach.py`: consent validation and dry-run / explicitly enabled sending.
- `templates.json`: message templates.
- `leads.csv`: inert sample row with consent disabled.
- `tests/test_outreach.py`: consent and dry-run tests.
- `.github/workflows/outreach.yml`: manual workflow.

## Dry-run
`python outreach.py --csv leads.csv`

Email variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`.
WhatsApp variables: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEMPLATE_NAME`, `WHATSAPP_LANGUAGE`.

Do not send unsolicited messages. Follow platform policies and applicable laws. Test only with recipients who have explicitly agreed to receive messages.
