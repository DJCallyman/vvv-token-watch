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
The test clears only the application tables in that database.
