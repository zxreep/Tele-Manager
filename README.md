# Tele-Manager

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
