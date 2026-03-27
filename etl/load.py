import time
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger
from etl.config import DB_URL

LOAD_ORDER = [
    'dim_date',
    'dim_recruitment',
    'dim_termination',
    'dim_manager',
    'dim_performance',
    'dim_job',
    'dim_employee',
    'fact_employee_attrition',
]

def load_all(tables: dict) -> None:
    """
    Charge toutes les tables dans l'ordre défini par LOAD_ORDER.
    Effectue un TRUNCATE complet avant insertion.
    """
    # Vérification que toutes les tables nécessaires sont présentes
    missing = [t for t in LOAD_ORDER if t not in tables]
    if missing:
        raise ValueError(f"Tables manquantes dans le dictionnaire : {missing}")

    engine = create_engine(DB_URL)
    start_time = time.time()

    try:
        with engine.begin() as conn:
            logger.info("Nettoyage des tables (TRUNCATE CASCADE)...")
            # On vide d'abord la table de faits
            conn.execute(text("TRUNCATE TABLE fact_employee_attrition CASCADE"))
            # Puis les dimensions dans l'ordre inverse pour respecter les contraintes FK
            for name in reversed(LOAD_ORDER[:-1]):
                conn.execute(text(f"TRUNCATE TABLE {name} CASCADE"))

            logger.info("Chargement des tables...")
            for name in LOAD_ORDER:
                df = tables[name]
                if df.empty:
                    logger.warning(f"La table {name} est vide, aucun chargement effectué.")
                    continue

                start_table = time.time()
                df.to_sql(
                    name, conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=500,
                )
                count = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
                elapsed = time.time() - start_table
                logger.success(f"  {name:<35} {count:>7} lignes ({elapsed:.2f}s)")

        elapsed_total = time.time() - start_time
        logger.success(f"Chargement terminé en {elapsed_total:.2f} secondes.")

    except Exception as e:
        logger.error(f"Erreur lors du chargement : {e}")
        # La transaction sera automatiquement annulée par le with engine.begin()
        raise

    finally:
        engine.dispose()
        logger.info("Connexion fermée.")


def verify(engine) -> None:
    """Requêtes de contrôle post-chargement (inchangées)."""
    queries = {
        "Vue d'ensemble": """
            SELECT
                COUNT(*)                                              AS total_employes,
                SUM(attrition_flag)                                   AS nb_departs,
                ROUND(100.0*SUM(attrition_flag)/COUNT(*),1)           AS taux_attrition_pct,
                ROUND(AVG(salary)::numeric, 0)                        AS salaire_moyen,
                ROUND(AVG(engagement_survey)::numeric, 2)             AS engagement_moyen,
                ROUND(AVG(absences)::numeric, 1)                      AS absences_moyennes
            FROM fact_employee_attrition
        """,
        "Attrition par département": """
            SELECT
                j.department,
                COUNT(*)                                              AS total,
                SUM(f.attrition_flag)                                 AS departs,
                ROUND(100.0*SUM(f.attrition_flag)/COUNT(*),1)         AS taux_pct
            FROM fact_employee_attrition f
            JOIN dim_job j ON f.job_key = j.job_key
            GROUP BY j.department
            ORDER BY taux_pct DESC
        """,
        "Départs par année": """
            SELECT
                d.year,
                COUNT(*)                                              AS nb_departs
            FROM fact_employee_attrition f
            JOIN dim_date d ON f.departure_date_key = d.date_key
            WHERE f.attrition_flag = 1
              AND d.year < 9999
            GROUP BY d.year
            ORDER BY d.year
        """,
        "Attrition par source recrutement": """
            SELECT
                r.recruitment_source,
                r.source_category,
                COUNT(*)                                              AS total,
                SUM(f.attrition_flag)                                 AS departs,
                ROUND(100.0*SUM(f.attrition_flag)/COUNT(*),1)         AS taux_pct
            FROM fact_employee_attrition f
            JOIN dim_recruitment r ON f.recruitment_key = r.recruitment_key
            GROUP BY r.recruitment_source, r.source_category
            ORDER BY taux_pct DESC
        """,
        "Role-playing dim_date — intégrité": """
            SELECT
                COUNT(*) FILTER (WHERE hire_date_key = -1)        AS hire_nulls,
                COUNT(*) FILTER (WHERE departure_date_key = -1)   AS depart_nulls,
                COUNT(*) FILTER (WHERE last_review_date_key = -1) AS review_nulls
            FROM fact_employee_attrition
        """,
    }

    with engine.connect() as conn:
        for label, sql in queries.items():
            result = pd.read_sql(text(sql), conn)
            logger.info(f"\n{'─'*50}\n{label}\n{result.to_string(index=False)}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from etl.extract import extract
    from etl.transform import (
        build_dim_employee, build_dim_job, build_dim_manager,
        build_dim_recruitment, build_dim_termination,
        DIM_PERFORMANCE,
    )
    from etl.transform import build_fact
    from etl.dim_date import build_dim_date

    logger.info("=== Lancement du test complet ETL (extract → transform → load) ===")
    status = {"etape": None, "succes": False, "erreur": None}

    try:
        status["etape"] = "extraction"
        df_raw = extract()

        status["etape"] = "transformation"
        dim_date        = build_dim_date()
        dim_employee    = build_dim_employee(df_raw)
        dim_job         = build_dim_job(df_raw)
        dim_manager     = build_dim_manager(df_raw)
        dim_recruitment = build_dim_recruitment(df_raw)
        dim_termination = build_dim_termination(df_raw)
        fact            = build_fact(
            df_raw, dim_employee, dim_job, dim_manager,
            dim_recruitment, dim_termination, DIM_PERFORMANCE
        )

        status["etape"] = "chargement"
        tables = {
            'dim_date':                dim_date,
            'dim_recruitment':         dim_recruitment,
            'dim_termination':         dim_termination,
            'dim_manager':             dim_manager,
            'dim_performance':         DIM_PERFORMANCE,
            'dim_job':                 dim_job,
            'dim_employee':            dim_employee,
            'fact_employee_attrition': fact,
        }
        load_all(tables)

        status["etape"] = "verification"
        engine = create_engine(DB_URL)
        verify(engine)
        engine.dispose()

        status["succes"] = True

    except Exception as e:
        status["erreur"] = str(e)

    finally:
        logger.info("─" * 50)
        if status["succes"]:
            logger.success(f"RÉSULTAT : SUCCÈS — toutes les étapes ont été complétées.")
        else:
            logger.error(f"RÉSULTAT : ÉCHEC — étape '{status['etape']}' | erreur : {status['erreur']}")