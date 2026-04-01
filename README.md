# Tele-Manager

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

This project reads the PostgreSQL connection string from `NEON_DATABASE_URL`.

```bash
export NEON_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require'
```

### Install dependencies

```bash
pip install sqlalchemy alembic psycopg[binary]
```

### Run migrations

```bash
alembic upgrade head
```

### Create a new migration

```bash
alembic revision -m "your migration message"
```

Initial migration: `alembic/versions/0001_initial_schema.py`.

## Added tables

- `users`
- `groups`
- `memberships`
- `broadcast_jobs`
- `broadcast_targets`
- `events`
- `premium_subscriptions`

## Repository helpers

`tele_manager/repository.py` includes:

- Upsert user/group on activity.
- Fetch admin/premium flags.
- List target groups/channels for broadcasts.
- Analytics counters (DAU/WAU, total groups, active users).
