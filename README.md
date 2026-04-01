# Tele-Manager

Telegram bot deployment and operations notes.
## Contribution notes

Use the structure below to keep feature additions isolated and maintainable.

### Add a new command handler

1. Create a new handler module in `bot/handlers/` (for example `bot/handlers/help.py`).
2. Expose the module router in that file (for example `router = Router()`).
3. Register it in `bot/handlers/__init__.py` by adding a key/value to `ROUTER_REGISTRY`.
4. If the command is gated, tie it to a feature flag in `bot/config.py`.
5. Add tests in:
   - `tests/unit/` for any command-specific service logic.
   - `tests/integration/` for end-to-end handler behavior with mocked Telegram API.

### Add a new DB model or migration

1. Add the new model under your data layer module (for example `bot/db/models/`).
2. Create a migration in your migration tool's directory (for example `migrations/`).
3. Update relevant repository/service implementations to use the model.
4. Add/update unit tests for repositories/services in `tests/unit/`.
5. Add integration coverage for affected handlers in `tests/integration/`.

### Add a new admin panel section

1. Add/update admin handler module(s) under `bot/handlers/`.
2. Place business logic behind interfaces in `bot/services/interfaces.py` and implement in concrete services.
3. Register new admin routes via `bot/handlers/__init__.py`.
4. Gate access through role/permission checks and optional feature flags in `bot/config.py`.
5. Add integration tests for admin flows in `tests/integration/`.

## Bootstrap architecture added for future features

- Central router registry: `bot/handlers/__init__.py`
- Feature flags: `bot/config.py`
- Service protocols: `bot/services/interfaces.py`
- Test skeletons: `tests/unit/`, `tests/integration/`
## Database setup (Neon + SQLAlchemy + Alembic)

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
   export DATABASE_URL="<postgres-connection-string>"
   export ADMIN_IDS="123456789,987654321"
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
4. Save it as `DATABASE_URL` in local shell and in Render environment variables.

## Alembic migration run

1. Ensure `DATABASE_URL` points to the target Neon database.
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
   - `DATABASE_URL`
   - `ADMIN_IDS`
   - `LOG_LEVEL` (e.g. `INFO`)
6. Create the service and wait for initial build + deploy.
7. Trigger a manual deploy after each migration if schema changed.

## Health and logging strategy

### Structured logs to stdout

- Emit JSON-formatted logs to stdout so Render captures logs natively.
- Include standard fields such as `timestamp`, `level`, `logger`, `message`, and optional context (`chat_id`, `user_id`, `update_id`).
- Keep `LOG_LEVEL` configurable from environment.

### Startup DB connectivity check

- On startup, attempt a lightweight connectivity probe (e.g., `SELECT 1`) using `DATABASE_URL`.
- Exit with a non-zero code if the check fails so Render marks the deployment unhealthy and retries according to its policy.
- Log success/failure of the DB check as a structured startup event.
