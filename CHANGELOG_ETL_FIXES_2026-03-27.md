# ETL Fixes - 2026-03-27

## Scope
This update addresses three reliability issues identified during ETL review.

## Changes Applied

### 1) Quality checks no longer hard-fail when `fact_key` is missing
- File: `etl/quality.py`
- Added helper: `column_exists(engine, table_name, column_name)`.
- Updated `run_all_quality_checks`:
  - If `fact_employee_attrition.fact_key` exists, duplicate-key check is executed.
  - If it does not exist, a warning is logged and ETL quality checks continue.

Why:
- Prevents post-load failure in environments where the migration adding `fact_key` was not yet applied.

### 2) Safe sentinel date for pandas
- File: `etl/dim_date.py`
- Added constant: `PANDAS_MAX_SAFE_DATE = pd.Timestamp('2262-04-11')`.
- Replaced sentinel `full_date` from `9999-12-31` to `2262-04-11`.
- Updated sentinel `year` from `9999` to `2262`.

Why:
- Avoids potential `OutOfBoundsDatetime` errors on pandas builds that cannot represent year 9999.

### 3) Migration runner made robust against semicolons in SQL
- File: `etl/migrate.py`
- Removed manual SQL splitting with `sql_content.split(';')`.
- Now executes each migration file as a full SQL script using the DB driver cursor.

Why:
- Avoids parsing bugs with function/procedure bodies or quoted strings that contain semicolons.
- Delegates SQL parsing to PostgreSQL, which is the reliable parser.

## Notes
- This change set intentionally focuses on runtime resilience and migration robustness.
- Existing ETL flow and data model behavior remain unchanged outside the fixes above.
