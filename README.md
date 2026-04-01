# Tele-Manager

Telegram bot deployment and operations notes.

## Local setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure local environment variables:
   ```bash
   export BOT_TOKEN="<telegram-bot-token>"
   export NEON_DATABASE_URL="<postgres-connection-string>"
   export SUPERADMIN_IDS="123456789,987654321"
   export LOG_LEVEL="INFO"
   ```
4. Run the bot locally:
   ```bash
   python -m bot.main
   ```

## Neon DB provisioning

1. Create a Neon project and Postgres database.
2. Create a dedicated database role for the bot with least privileges required for runtime and migrations.
3. Copy the Neon pooled or direct connection string.
4. Save it as `NEON_DATABASE_URL` in local shell and in Render environment variables.

## Alembic migration run

1. Ensure `NEON_DATABASE_URL` points to the target Neon database.
2. Run migrations before starting a new deployment:
   ```bash
   alembic upgrade head
   ```
3. Verify migration status:
   ```bash
   alembic current
   ```

## Render deployment (step-by-step)

1. Push this repository to GitHub/GitLab.
2. In Render, click **New +** → **Blueprint** and select the repository.
3. Render will detect `render.yaml` and propose a **Worker** service.
4. Confirm settings:
   - Runtime: `python`
   - Build command: `pip install -r requirements.txt`
   - Start command: `python -m bot.main`
5. Set environment variables in Render:
   - `BOT_TOKEN`
   - `NEON_DATABASE_URL`
   - `SUPERADMIN_IDS`
   - `LOG_LEVEL` (e.g. `INFO`)
6. Create the service and wait for initial build + deploy.
7. Trigger a manual deploy after each migration if schema changed.

## Health and logging strategy

### Structured logs to stdout

- Emit JSON-formatted logs to stdout so Render captures logs natively.
- Include standard fields such as `timestamp`, `level`, `logger`, `message`, and optional context (`chat_id`, `user_id`, `update_id`).
- Keep `LOG_LEVEL` configurable from environment.

### Startup DB connectivity check

- On startup, attempt a lightweight connectivity probe (e.g., `SELECT 1`) using `NEON_DATABASE_URL`.
- Exit with a non-zero code if the check fails so Render marks the deployment unhealthy and retries according to its policy.
- Log success/failure of the DB check as a structured startup event.
