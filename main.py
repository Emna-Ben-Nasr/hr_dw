"""
ETL HR Attrition — HRDataset v14
Exécution : python main.py
"""
import os
from loguru import logger
from sqlalchemy import create_engine

from etl.config    import DB_URL
from etl.extract   import extract
from etl.dim_date  import build_dim_date
from etl.transform import (
    build_dim_employee, build_dim_job, build_dim_manager,
    build_dim_recruitment, build_dim_termination, DIM_PERFORMANCE,
    build_fact, SNAPSHOT_DATE
)
from etl.load      import load_all, verify, LOAD_ORDER
from etl.quality   import run_all_quality_checks   # nouveau


if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    logger.add('logs/etl_{time:YYYY-MM-DD_HH-mm}.log',
               rotation='1 day', level='DEBUG', encoding='utf-8')

    logger.info("=" * 55)
    logger.info("  ETL HRDataset v14 — démarrage")
    logger.info("=" * 55)

    # ── 1. EXTRACT ────────────────────────────────────────────────
    logger.info("── ÉTAPE 1 : Extraction ──")
    df_raw = extract()

    # ── 2. TRANSFORM — dimensions ─────────────────────────────────
    logger.info("── ÉTAPE 2 : Transformation des dimensions ──")
    dim_date        = build_dim_date()
    dim_employee    = build_dim_employee(df_raw)
    dim_job         = build_dim_job(df_raw)
    dim_manager     = build_dim_manager(df_raw)
    dim_recruitment = build_dim_recruitment(df_raw)
    dim_termination = build_dim_termination(df_raw)
    dim_performance = DIM_PERFORMANCE.copy()

    # ── 3. TRANSFORM — table de faits ────────────────────────────
    logger.info("── ÉTAPE 3 : Construction de la table de faits ──")
    fact = build_fact(
        df_raw,
        dim_employee, dim_job, dim_manager,
        dim_recruitment, dim_termination, dim_performance,
    )

    # ── 4. LOAD ──────────────────────────────────────────────────
    logger.info("── ÉTAPE 4 : Chargement PostgreSQL ──")
    tables = {
        'dim_date':               dim_date,
        'dim_recruitment':        dim_recruitment,
        'dim_termination':        dim_termination,
        'dim_manager':            dim_manager,
        'dim_performance':        dim_performance,
        'dim_job':                dim_job,
        'dim_employee':           dim_employee,
        'fact_employee_attrition': fact,
    }
    load_all(tables)

    # ── 5. VÉRIFICATION POST-CHARGE ──────────────────────────────
    logger.info("── ÉTAPE 5 : Vérification et qualité des données ──")
    engine = create_engine(DB_URL)
    verify(engine)                     # requêtes métier existantes
    run_all_quality_checks(engine)     # nouveaux contrôles approfondis
    engine.dispose()

    logger.info("=" * 55)
    logger.info("  ETL TERMINÉ AVEC SUCCÈS")
    logger.info("=" * 55)