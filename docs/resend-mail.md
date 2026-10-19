# Lotus outgoing mail

Native Frappe Email Account `Lotus Agritech` relays via `smtp.resend.com:465` with TLS, username `resend`, and the Resend API key as the SMTP password. The password is encrypted by Frappe; no API key belongs in Git or frontend assets.

Sender: `Lotus Agritech <no-reply@lotus.gpcds.site>`. Domain id: `6294fb81-c7bc-4f2a-8682-4410dd4fdeeb`.

Run `tools/configure_resend.py /private/path/to/key` using the site's Python from the bench sites directory. Configuration only enables outgoing/default mail after the Resend domain reports `verified`. Re-run after DNS verification. Frappe validates the SMTP connection on activation. Credentials are copied into the encrypted Email Account; remove the temporary credential file from the container afterward.

The setup creates five native Email Templates. System Settings selects the password reset and welcome templates, keeping Frappe's native single-use reset tokens, expiry, MFA and throttling. General notification, work reminder, and approval templates are available to native Email/Notification workflows; installing templates does not subscribe every user or enable unsolicited mail.

Public `host_name` must be `https://lotus.gpcds.site` so links and logos use the public URL. Queue workers and the scheduler handle queued mail. Inspect Email Queue and Resend for delivery; SMTP acceptance alone does not establish inbox delivery.

DNS in `gpcds.site`: `resend._domainkey.lotus` TXT (DKIM value from Resend), `rsend.lotus` CNAME to `rsend-apne1.forge.rmta.net`, `send.lotus` CNAME to `send.forge.rmta.net`. CNAME records must use DNS only. Public DNS already returned all three on 2026-10-19; Resend initially reported pending and a verification request was submitted.

Docs: https://resend.com/docs/send-with-smtp
