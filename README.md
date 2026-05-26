# TextGPT

**SMS to LLM gateway with multi model routing, deployed to AWS EC2.**
Users text a Twilio number and get responses routed across multiple OpenAI models (text completion, chat, image generation) based on a custom command syntax. Built as a single Flask service, deployed to production, used by friends and strangers.

---

## Why this exists

I wanted to know if I could put a useful LLM in the pocket of anyone with a phone. No app. Just cell service. Texting a number is the lowest friction interface that exists. So I built it, and there was no other service like it.

---

## What it does

A user texts a Twilio number. The Flask server receives the webhook, parses the message, and routes it based on a command syntax I designed for SMS users:

| Prefix | Behavior |
|---|---|
| *(none)* | Routes to `text-davinci-003` with default params |
| `!!` | Routes to `gpt-3.5-turbo` with a system prompt and persistent conversation history |
| `@@` | Routes to DALL-E, returns image URL via MMS |
| `$$` | Returns help text describing the command syntax |
| `::temp:model:max_tokens` | Override defaults per message (e.g. `What is recursion? ::0.2:gpt4:500`) |

Every request is logged to SQLite with hashed user/sender identifiers, token usage, model, temperature, and finish reason. Both for cost tracking and for later analysis of how users actually use the system.

---

## Architecture

```
[User SMS] → [Twilio] → [Ngrok tunnel / EC2 public endpoint]
                            ↓
                      [Flask /sms webhook]
                            ↓
                   [Parse + route by prefix]
                            ↓
        ┌────────────────┬─────────────────┬───────────────┐
        ↓                ↓                 ↓               ↓
   [text-davinci-3]  [gpt-3.5-turbo]   [DALL-E]      [help text]
        ↓                ↓                 ↓
        └────────────────┴─────────────────┘
                            ↓
                  [Log to SQLite + reply via Twilio]
```

**Deployment:** Flask app runs on AWS EC2 (Amazon Linux). The codebase detects platform at startup, `Linux` vs `Darwin` (MacOS) and adjusts file paths accordingly as I may be running it from a different machine with a different operating system. So the same source runs locally for development and remotely in production with no code changes.

**Secrets:** ConfigParser reads `CONFIG_APIS.ini` with separate sections for OpenAI, Twilio, and Ngrok. The config file lives outside the repo and is never committed, you know, because secrets.

**Privacy:** Sender phone numbers are SHA-257 hashed before being written to the database. Plain phone numbers exist only in the in memory request object long enough to send the reply.

---

## Production problems I had to solve

These are the things that broke when real users started texting it. The fixes are what made it actually work:

**iMessage tapback pollution.** When iPhone users react to a message with "Loved", "Liked", "Laughed at", etc., those reactions arrive as new SMS messages prefixed with `Loved "original message text"`. Without filtering, the bot would treat the tapback as a new question and respond to itself. So I added a tapback filter that strips these prefixes before the message hits the LLM, verryyyyy handy.

**OpenAI rate limits during peak hours.** Hit `RateLimitError` in production when too many users texted in a short window. I caught the trace, kept it in source as documentation, and learned the hard way that LLM API calls need retry logic. Not just for the local code, but to give the *user* a sensible response when upstream fails instead of just dropping their message.

**Free tier ngrok tunnel collisions.** Ngrok's free tier limits the number of active tunnels. On reconnects, old tunnels weren't being cleaned up, so new ones failed to bind. I added port check guidance and tunnel kill logic to startup. The Ngrok service was quite excellent, but now days I use the cloudflared package for local testing.

**Python version differences across environments.** EC2's Python 3.7 doesn't support `str.removeprefix()` (added in 3.9). I wrapped the response parsing in a try/except so the same code runs on both interpreters without a compatibility shim everywhere.

**Multi-turn chat state.** For the `!!` ChatGPT route, conversation history needs to persist across SMS messages, but SMS is stateless. Tracked `message_log` server-side keyed off the running instance. I documented limitation: history resets when the server restarts (acceptable for v1, would move to per-user persistence for v2).

---

## Tech stack

- **Python 3.7+** (Flask, requests, sqlite3, hashlib, configparser, logging)
- **Twilio** SMS messaging service (webhooks for inbound, REST API for outbound)
- **OpenAI API** (Completion, ChatCompletion, Image Generation)
- **Ngrok** for local dev tunneling; direct public endpoint in production
- **SQLite** for request logging and analytics
- **AWS EC2** (Amazon Linux) for production deployment
- **tiktoken / GPT2TokenizerFast** for token counting

---

## What I'd build differently today

- **Replace ngrok dependency in production** with a proper reverse proxy + domain (was a holdover from local dev).
- **Move secrets to AWS Parameter Store or Secrets Manager** instead of a config file on disk.
- **Add retry logic with exponential backoff** for OpenAI calls (the rate limit error in production should have failed gracefully, not 500'd).
- **Switch SQLite to PostgreSQL on RDS** for production — SQLite is fine for a single instance but blocks horizontal scaling.
- **Add structured logging** (JSON to stdout, ingested by CloudWatch) instead of file based logs.
- **Move from `Completion.create` to `ChatCompletion.create` everywhere** — text-davinci-003 is deprecated and the Completion API has been sunset by OpenAI. The conversational models are now the standard.
- **Replace polling-style conversation state with per-user keys** in a Redis or DynamoDB layer, so history survives restarts and scales across instances.

---

## Running it (historical reference)

The deployment is no longer live. To run locally:

1. Create `CONFIG_APIS.ini` with `[OPENAI]`, `[TWILIO]`, and `[NGROK]` sections.
2. `pip install flask twilio openai pyngrok tiktoken transformers requests pyperclip`
3. `python OpenAI.py` — starts the Flask app and ngrok tunnel, configures the Twilio webhook automatically.
4. Text the configured Twilio number.

---

## What this project taught me

- Designing a user facing command syntax for a channel (SMS) that has no UI at all.
- Production debugging when the "users" are real people who don't know to send you a bug report.
- The gap between "API works in Postman" and "API works when a user sends an iMessage tapback at 11pm on a Tuesday."
- Cost conscious LLM usage at the per request level, because someone has to pay the bill.
- Always use some form of version control because copies of copies of old working version don't cut it.
