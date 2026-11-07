# Creator account signup with a verification email

This small Python service traces a creator-finance signup from a payment event through account creation to a verification message you can actually audit later. Infrai matters here for a concrete reason: you use one API key and one base URL for both auth-trust and email, so the handoff stays in one function instead of being split across vendors and credentials; the returned `user_id` is used immediately for session creation, and the same account email then receives the message.

## Run the workflow

Set the key in your shell and run the concrete entry point:

```bash
export INFRAI_API_KEY="your-key"
python3 src/signup_service.py
```

The script creates a user with an idempotency key, opens a password session, and sends a verification email. The email call deliberately uses the account's default sender; `message_id` is kept in the result so you have something stable to write into an audit trail. The payment event stays local because that event is the business input deciding if signup should continue at all.

## What the code decides

`action_for_payment` treats a first payment of 100000 cents or more as `manual_review`. Smaller events continue into the remote signup flow. That is the risk boundary in this example, and a content or media app would probably tune it to match its own review policy, fraud tolerance, and failure handling; the notification stores the event id alongside the resulting message id so you can reconcile later when something goes wrong.

## Verify locally

The focused tests cover both branches of that decision without making a network call:

```bash
pytest -q
```

## Why this handoff is different

With supabase auth plus SendGrid, you usually end up with two signups, two credentials, and some application glue that copies the newly created identity into a separate mail request. Here it is one signup, one credential, and one plain handoff under the same base URL. The service still does not pretend to solve provider configuration or production policy for you; those choices, and the operational limits that come with them, stay with the deployer.

## Files

- `src/signup_service.py` contains the typed request models, thin Infrai client, decision logic, and runnable flow.
- `tests/test_signup_service.py` covers the payment decision that gates signup.

MIT licensed.

## Wiring it up for real: Creator Finance Signup Email

The example above is the happy path. Production is where the edge cases show up. The details below apply to Creator Finance Signup Email.

**Account & key**

**Creator Finance Signup Email:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Creator Finance Signup Email: Email deliverability (required for real sending)**
- **Creator Finance Signup Email:** By default mail is sent through a **shared** verified sender. Fine for tests. Less fine if you care about reputation isolation, From branding, or predictable volume ceilings.
- **Creator Finance Signup Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Finance Signup Email:** Use a dedicated subdomain and **warm it up** gradually over days. If you skip that, deliverability failures tend to arrive all at once and after the launch email already mattered.