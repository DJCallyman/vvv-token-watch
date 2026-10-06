# Database migrations

The API applies Alembic migrations during startup. A fresh PostgreSQL database
is created by the initial migration. For an existing unversioned installation,
startup verifies that the current application tables and columns are present,
stamps the initial baseline without changing table data, and then applies
forward migrations. The baseline allows the historical `earned_credits`
column to be absent; the next migration adds it without dropping data.

Back up the database before upgrading. If the existing schema is incomplete or
does not match the supported baseline, startup stops and logs the missing
tables or columns. Reconcile that schema before restarting; do not stamp an
unverified database.

For a fresh database, migrations can also be applied manually from the
repository root with:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

To run the PostgreSQL migration integration test, set
`MIGRATION_TEST_DATABASE_URL` to a dedicated, disposable PostgreSQL database.
The test drops and recreates the application tables in that database. Never
point it at the normal development or production database.

For local development, start the PostgreSQL service and create a separate test
database. Activate the project's Python environment first. If the test
dependencies are not installed, install them from the repository root:

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

Start PostgreSQL and wait until it accepts connections:

```bash
docker compose -f docker-compose.dev.yml up -d postgres
docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U vvvwatch -d vvvwatch
```

Then create the dedicated database:

```bash
docker compose -f docker-compose.dev.yml exec -T postgres psql -U vvvwatch -d postgres \
	-c "CREATE DATABASE vvvwatch_migration_test"
```

From the repository root, run the test with the test database URL:

```bash
MIGRATION_TEST_DATABASE_URL=postgresql+asyncpg://vvvwatch:vvvwatch@localhost:5433/vvvwatch_migration_test \
	PYTHONPATH=. pytest backend/tests/test_migrations.py -v
```

The test skips when `MIGRATION_TEST_DATABASE_URL` is unset. After the test,
remove the dedicated database if you no longer need it:

```bash
docker compose -f docker-compose.dev.yml exec -T postgres psql -U vvvwatch -d postgres \
	-c "DROP DATABASE vvvwatch_migration_test"
```
