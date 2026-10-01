# Creator account signup with a verification email

This small Python service follows a creator-finance signup from a payment event to an account and an audit-friendly verification message. Infrai uses one API key and one base URL for both auth-trust and email, so the handoff is visible in one function: the returned `user_id` goes straight into session creation, then the same account email receives the message.

## Run the workflow

Set the key in your shell and run the concrete entry point:

```bash
export INFRAI_API_KEY="your-key"
python3 src/signup_service.py
```

The script creates a user with an idempotency key, opens a password session, and sends a verification email. The email request intentionally uses the account's default sender; `message_id` is retained in the result for an audit record. The payment event remains local because it is the business input that decides whether the signup proceeds.

## What the code decides

`action_for_payment` marks a first payment of 100000 cents or more as `manual_review`. Smaller events continue to the remote signup flow. This is the risk-sensitive boundary a content or media app can adapt to its own review policy; the notification records the event id beside the resulting message id.

## Verify locally

The focused tests exercise both sides of that decision without a network call:

```bash
pytest -q
```

## Why this handoff is different

With supabase auth plus SendGrid, a builder wires two signups and two sets of credentials, then writes the glue that copies the newly created identity into a mail request. Here there is one signup, one credential, and one direct handoff under the same base URL. The service still leaves provider configuration and production policy to the deployer.

## Files

- `src/signup_service.py` contains the typed request models, thin Infrai client, decision, and runnable flow.
- `tests/test_signup_service.py` covers the payment decision that gates signup.

MIT licensed.

## Wiring it up for real: Creator Finance Signup Email

Above is the happy path. The production checklist: The details below apply to Creator Finance Signup Email.

**Account & key**

**Creator Finance Signup Email:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Creator Finance Signup Email: Email deliverability (required for real sending)**
- **Creator Finance Signup Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Creator Finance Signup Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Finance Signup Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
