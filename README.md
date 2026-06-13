# HR Attrition Datamart

> Academic group project — Data Modeling & ETL module

---

## About

👥 A star-schema datamart for HR attrition analysis — built from raw CSV data with a custom Python ETL pipeline, database migrations, and automated quality checks feeding into a `fact_employee_attrition` table ready for BI tools.

---

## Data model

The datamart is centered on a single fact table with multiple dimensions:

```
                    ┌─────────────────┐
                    │ dim_employee    │
                    └────────┬────────┘
                             │
┌──────────────┐    ┌────────▼──────────────┐    ┌──────────────────┐
│  dim_job     ├────►  fact_employee_        ◄────┤  dim_performance │
└──────────────┘    │     attrition         │    └──────────────────┘
                    └────────┬──────────────┘
                    ┌────────┴────────┐
              ┌─────▼─────┐   ┌──────▼──────┐
              │ dim_date  │   │ dim_dept     │
              └───────────┘   └─────────────┘
```

**Key KPIs exposed:** attrition rate, performance distribution, job-level turnover, seniority-based attrition, department breakdown.

---

## ETL pipeline

```
data/raw/ (CSV)
      │
      ▼
   Extract          ← read raw HR data files
      │
      ▼
   Transform        ← clean, normalize, compute attrition metrics
      │
      ▼
   Migrations       ← apply schema changes via migration runner
      │
      ▼
   Load             ← insert into star-schema tables
      │
      ▼
   Quality checks   ← validate data integrity post-load
```

- `main.py` — pipeline entry point (extract → transform → migrate → load → quality checks)
- `etl/` — modular ETL logic (transform, load, dim_date, quality, migrate)
- `migrations/` — versioned SQL schema migrations
- `data/raw/` — source CSV files

---

## Tech stack

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=flat&logo=postgresql&logoColor=white)

---

## Getting started

### Prerequisites

- Python 3.10+
- PostgreSQL running locally

### 1. Clone and set up virtual environment

```bash
git clone https://github.com/Emna-Ben-Nasr/hr_dw.git
cd hr_dw

python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# or
venv\Scripts\activate           # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Test database connection

```bash
python test_connexion.py
```

### 4. Run the full ETL pipeline

```bash
python main.py
```

This will apply all migrations, run the ETL, and execute post-load quality checks automatically.

---

## Project structure

```
├── data/
│   └── raw/                         # Source CSV files
├── etl/
│   ├── transform.py                 # Data cleaning & normalization
│   ├── load.py                      # Load into fact & dimension tables
│   ├── dim_date.py                  # Date dimension generation
│   ├── quality.py                   # Post-load data quality checks
│   └── migrate.py                   # Migration runner
├── migrations/                      # Versioned SQL schema files
├── logs/                            # ETL run logs
├── main.py                          # Pipeline entry point
├── test_connexion.py                # DB connection test
├── requirements.txt
└── CHANGELOG_ETL_FIXES_2026-03-27.md
```

---

## Context

Developed as part of the Master's in Information Systems & Knowledge Engineering at **FSEGN** (Faculty of Economic Sciences and Management of Nabeul, Tunisia).
