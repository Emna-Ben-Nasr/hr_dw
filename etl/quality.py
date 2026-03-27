import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Vérifie la présence d'une colonne dans une table PostgreSQL."""
    sql = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            'table_name': table_name,
            'column_name': column_name,
        }).scalar() is not None

def check_row_count(engine, table_name: str, expected_min: int = 0, expected_max: int = None):
    """Vérifie que le nombre de lignes dans une table est dans une fourchette."""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
    logger.info(f"{table_name}: {count} lignes")
    if count < expected_min:
        logger.error(f"{table_name}: nombre de lignes ({count}) inférieur au minimum attendu ({expected_min})")
        raise ValueError(f"Row count trop bas pour {table_name}")
    if expected_max is not None and count > expected_max:
        logger.error(f"{table_name}: nombre de lignes ({count}) supérieur au maximum attendu ({expected_max})")
        raise ValueError(f"Row count trop élevé pour {table_name}")

def check_fk_integrity(engine, fact_table: str, dim_tables: dict):
    """
    Vérifie que toutes les clés étrangères dans la table de faits existent dans les dimensions.
    dim_tables = {'fact_fk_col': ('nom_dimension', 'dim_pk_col')}
    """
    with engine.connect() as conn:
        for fk_col, (dim, dim_pk) in dim_tables.items():
            sql = text(f"""
                SELECT COUNT(*) FROM {fact_table} f
                LEFT JOIN {dim} d ON f.{fk_col} = d.{dim_pk}
                WHERE d.{dim_pk} IS NULL
            """)
            result = conn.execute(sql)
            null_count = result.scalar()
            if null_count > 0:
                logger.error(f"Intégrité référentielle : {null_count} valeurs de {fk_col} sans correspondance dans {dim}.{dim_pk}")
                raise ValueError(f"FK violée : {fk_col} -> {dim}.{dim_pk}")

def check_duplicate_keys(engine, table_name: str, key_column: str):
    """Vérifie l'absence de doublons sur une colonne clé."""
    with engine.connect() as conn:
        sql = text(f"""
            SELECT {key_column}, COUNT(*)
            FROM {table_name}
            GROUP BY {key_column}
            HAVING COUNT(*) > 1
        """)
        result = conn.execute(sql)
        duplicates = result.fetchall()
        if duplicates:
            logger.error(f"Doublons trouvés dans {table_name} sur {key_column} : {duplicates}")
            raise ValueError(f"Doublons dans {table_name}.{key_column}")

def run_all_quality_checks(engine):
    """Exécute tous les contrôles de qualité."""
    logger.info("Début des contrôles de qualité post‑chargement")

    # Vérifications des tailles minimales
    check_row_count(engine, 'dim_date', expected_min=1000)          # au moins 1000 dates
    check_row_count(engine, 'dim_employee', expected_min=300)
    check_row_count(engine, 'dim_job', expected_min=10)
    check_row_count(engine, 'dim_manager', expected_min=20)
    check_row_count(engine, 'dim_recruitment', expected_min=5)
    check_row_count(engine, 'dim_termination', expected_min=10)
    check_row_count(engine, 'dim_performance', expected_min=4, expected_max=4)
    check_row_count(engine, 'fact_employee_attrition', expected_min=300)

    # Vérification d'unicité des clés primaires
    check_duplicate_keys(engine, 'dim_employee', 'employee_key')
    check_duplicate_keys(engine, 'dim_job', 'job_key')
    check_duplicate_keys(engine, 'dim_manager', 'manager_key')
    check_duplicate_keys(engine, 'dim_recruitment', 'recruitment_key')
    check_duplicate_keys(engine, 'dim_termination', 'termination_key')
    check_duplicate_keys(engine, 'dim_performance', 'performance_key')
    if column_exists(engine, 'fact_employee_attrition', 'fact_key'):
        check_duplicate_keys(engine, 'fact_employee_attrition', 'fact_key')
    else:
        logger.warning(
            "fact_employee_attrition.fact_key absent — contrôle de doublons fact_key ignoré "
            "(migration non appliquée ?)"
        )

    # Vérification des FK
    fk_checks = {
        'employee_key':        ('dim_employee',    'employee_key'),
        'job_key':             ('dim_job',         'job_key'),
        'manager_key':         ('dim_manager',     'manager_key'),
        'recruitment_key':     ('dim_recruitment', 'recruitment_key'),
        'termination_key':     ('dim_termination', 'termination_key'),
        'performance_key':     ('dim_performance', 'performance_key'),
        'hire_date_key':       ('dim_date',        'date_key'),
        'departure_date_key':  ('dim_date',        'date_key'),
        'last_review_date_key':('dim_date',        'date_key'),
    }
    check_fk_integrity(engine, 'fact_employee_attrition', fk_checks)

    logger.success("Tous les contrôles de qualité sont passés avec succès")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from etl.config import DB_URL
    from sqlalchemy import create_engine

    engine = create_engine(DB_URL)
    try:
        run_all_quality_checks(engine)
    except ValueError as e:
        logger.error(f"ÉCHEC des contrôles qualité : {e}")
    finally:
        engine.dispose()