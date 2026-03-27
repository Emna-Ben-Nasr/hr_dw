import pandas as pd
from loguru import logger
from etl.config import DATE_RANGE_START, DATE_RANGE_END


def build_dim_date() -> pd.DataFrame:
    """
    Génère la dimension calendrier complète.
    Clé = entier YYYYMMDD.
    Ligne sentinelle date_key=-1 pour les dates manquantes (NULL).
    """
    logger.info(f"Génération dim_date : {DATE_RANGE_START} → {DATE_RANGE_END}")

    dates = pd.date_range(start=DATE_RANGE_START, end=DATE_RANGE_END, freq='D')
    df = pd.DataFrame({'full_date': dates})

    df['date_key']       = df['full_date'].dt.strftime('%Y%m%d').astype(int)
    df['day_num']        = df['full_date'].dt.day.astype('int16')
    df['day_name']       = df['full_date'].dt.day_name()
    df['week_num']       = df['full_date'].dt.isocalendar().week.astype('int16')
    df['month_num']      = df['full_date'].dt.month.astype('int16')
    df['month_name']     = df['full_date'].dt.month_name()
    df['quarter']        = 'Q' + df['full_date'].dt.quarter.astype(str)
    df['year']           = df['full_date'].dt.year.astype('int16')
    df['is_weekend']     = df['full_date'].dt.dayofweek >= 5
    df['fiscal_quarter'] = df['quarter']  # adapter si exercice décalé

    # Ligne sentinelle
    sentinel = pd.DataFrame([{
        'date_key': -1, 'full_date': pd.Timestamp('9999-12-31'),
        'day_num': 31, 'day_name': 'N/A', 'week_num': 53,
        'month_num': 12, 'month_name': 'N/A', 'quarter': 'Q4',
        'year': 9999, 'is_weekend': False, 'fiscal_quarter': 'Q4'
    }])

    dim = pd.concat([sentinel, df], ignore_index=True)
    logger.success(f"dim_date — {len(dim):,} lignes générées (dont sentinelle -1)")
    return dim


def date_to_key(series: pd.Series, null_key: int = -1) -> pd.Series:
    """Convertit une Series de dates en clés YYYYMMDD (int). NaT → null_key."""
    return pd.to_numeric(
        series.dt.strftime('%Y%m%d'), errors='coerce'
    ).fillna(null_key).astype(int)


if __name__ == "__main__":
    dim = build_dim_date()

    logger.info(f"Nombre de lignes  : {len(dim):,}")
    logger.info(f"Colonnes          : {list(dim.columns)}")
    logger.info(f"Première date     : {dim.loc[1, 'full_date'].date()}")
    logger.info(f"Dernière date     : {dim.iloc[-1]['full_date'].date()}")

    # Vérification sentinelle
    sentinel_row = dim[dim['date_key'] == -1]
    if sentinel_row.empty:
        logger.error("Sentinelle date_key=-1 introuvable !")
    else:
        logger.success("Sentinelle date_key=-1 présente")

    # Vérification unicité des clés
    if dim['date_key'].duplicated().any():
        logger.error("Doublons détectés dans date_key !")
    else:
        logger.success("date_key — toutes les clés sont uniques")

    # Test date_to_key
    test_dates = pd.to_datetime(pd.Series(['2020-01-15', '2023-06-30', None]))
    keys = date_to_key(test_dates)
    logger.info(f"date_to_key test  : {list(keys)}  (attendu: [20200115, 20230630, -1])")

    logger.success("=== Test dim_date terminé avec succès ===")
