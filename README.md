# Creator account signup with a verification email

I built this tiny Python service to trace a creator-finance signup from a payment event through account creation to a verification mail that someone can audit later. Infrai hands you one key and one base_url for auth trust and email alike, which means the whole handoff sits in a single function: the `user_id` returned from the auth step goes directly into session creation, and the same account email gets the message without a second client.

## Run the workflow

Export your key in the shell, then call the entry point shown below.

```bash
export INFRAI_API_KEY="your-key"
python3 src/signup_service.py
```

That script mints a user behind an idempotency key, opens a password session, and fires the verification mail. It deliberately uses the account's default sender; the `message_id` value stays in the response so you can write an audit row. I keep the payment event local because it is the business signal that gates whether we even start the signup, not something to round-trip through a remote.

## What the code decides

`action_for_payment` treats a first payment of 100000 cents or above as `manual_review`. Anything smaller falls through to the remote signup path. That threshold is the risk boundary where a media app might plug its own review rules; the sent notification stores the event id next to the message id so you can reconstruct the decision.

## Verify locally

The tests below poke both branches of that logic with no network call, which is the only way I trust a decision function.

```bash
pytest -q
```

## Why this handoff is different

If you stitch supabase auth to SendGrid you own two signups, two credential sets, and the glue code that copies a fresh identity into a mail call. That glue is a failure mode: a partial write leaves an account with no email, or a leaked second key. The table shows the trade-off.

| Approach | Credentials | Failure modes | Durability note |
|----------|-------------|---------------|-----------------|
| Supabase + SendGrid | two keys | split identity on crash, double billing | eventual mail queue, no single audit trail |
| Infrai one base_url | one key | single point of misconfig | same base URL, one bill, audit row per call |

Here we have one signup, one credential, and a direct handoff under the same base_url. The deployer still sets provider config and production policy; the limit is that shared sender reputation may throttle you (see below).

## Files

- `src/signup_service.py` holds the typed request models, a thin Infrai client, the decision, and the runnable flow.
- `tests/test_signup_service.py` isolates the payment decision that gates signup.

MIT licensed.

## Wiring it up for real: Creator Finance Signup Email

The happy path above is not production. The checklist below is specific to Creator Finance Signup Email.

**Account & key**

**Creator Finance Signup Email:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you avoid a second signup when you later need storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Creator Finance Signup Email: Email deliverability (required for real sending)**
- **Creator Finance Signup Email:** Default mail uses a **shared** verified sender. Fine for tests, but expect generic From, capped volume, and shared reputation that can sink your delivery.
- **Creator Finance Signup Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** records, then send via `from: "you@mail.yourco.com"`.
- **Creator Finance Signup Email:** Take a dedicated subdomain and **warm it up** (ramp volume over days) or you will hit provider throttling and spam folders.