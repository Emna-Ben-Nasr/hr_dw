import os
from pathlib import Path
from sqlalchemy import create_engine, text
from loguru import logger
from etl.config import DB_URL


def run_migrations():
    
    migrations_dir = Path(__file__).parent.parent / 'migrations'
    
    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return
    
    migration_files = sorted(migrations_dir.glob('*.sql'))
    
    if not migration_files:
        logger.warning("No migration files found")
        return
    
    engine = create_engine(DB_URL)
    
    try:
        with engine.begin() as conn:
            for migration_file in migration_files:
                logger.info(f"Running migration: {migration_file.name}")
                
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()

                try:
                    # Laisse PostgreSQL parser le script complet (plus robuste
                    # que le split manuel sur ';').
                    raw_conn = conn.connection
                    with raw_conn.cursor() as cursor:
                        cursor.execute(sql_content)
                    logger.debug("  Script SQL exécuté")
                except Exception as e:
                    logger.error(f"  Failed: {e}")
                    raise
                
                logger.success(f"  Migration {migration_file.name} completed")
        
        logger.success("All migrations completed successfully!")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    
    finally:
        engine.dispose()


if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    logger.add('logs/migrate_{time:YYYY-MM-DD_HH-mm}.log',
               rotation='1 day', level='DEBUG', encoding='utf-8')
    
    logger.info("=" * 55)
    logger.info("  Data Warehouse Migration")
    logger.info("=" * 55)
    
    run_migrations()
