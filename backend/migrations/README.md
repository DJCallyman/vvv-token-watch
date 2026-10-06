# Database migrations

The API runs Alembic migrations at startup. A fresh PostgreSQL database is
created by the initial migration. If an existing installation has no version
record,
startup checks that the application tables and columns exist. Startup then
stamps the initial baseline without changing table data and runs forward
migrations. The baseline allows the historical `earned_credits` column to be
absent. The next migration adds this column without dropping data.

Back up the database before an upgrade. If the schema is incomplete or does
not match the supported baseline, startup stops and logs the missing tables or
columns. Reconcile the schema before you restart the API. Do not stamp an
unverified database.

For a fresh database, run the migrations from the repository root:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Set `MIGRATION_TEST_DATABASE_URL` to a dedicated, disposable PostgreSQL
database to run the migration integration test. The test drops and recreates
the application tables in that database. Do not use the normal development or
production database.

Activate the project's Python environment. If the test dependencies are not
installed, install them from the repository root:

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

Start PostgreSQL. Then make sure it accepts connections:

```bash
docker compose -f docker-compose.dev.yml up -d postgres
docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U vvvwatch -d vvvwatch
```

Create the dedicated test database:

```bash
docker compose -f docker-compose.dev.yml exec -T postgres psql -U vvvwatch -d postgres \
	-c "CREATE DATABASE vvvwatch_migration_test"
```

From the repository root, run the test with the test database URL:

```bash
MIGRATION_TEST_DATABASE_URL=postgresql+asyncpg://vvvwatch:vvvwatch@localhost:5433/vvvwatch_migration_test \
	PYTHONPATH=. pytest backend/tests/test_migrations.py -v
```

The test skips if `MIGRATION_TEST_DATABASE_URL` is unset. After the test, drop
the dedicated database if you no longer need it:

```bash
docker compose -f docker-compose.dev.yml exec -T postgres psql -U vvvwatch -d postgres \
	-c "DROP DATABASE vvvwatch_migration_test"
```
