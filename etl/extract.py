import pandas as pd
from loguru import logger  
from etl.config import CSV_PATH

EXPECTED_COLS = [
    'Employee_Name', 'EmpID', 'MarriedID', 'MaritalStatusID', 'GenderID',
    'EmpStatusID', 'DeptID', 'PerfScoreID', 'FromDiversityJobFairID',
    'Salary', 'Termd', 'PositionID', 'Position', 'State', 'Zip',
    'DOB', 'Sex', 'MaritalDesc', 'CitizenDesc', 'HispanicLatino', 'RaceDesc',
    'DateofHire', 'DateofTermination', 'TermReason', 'EmploymentStatus',
    'Department', 'ManagerName', 'ManagerID', 'RecruitmentSource',
    'PerformanceScore', 'EngagementSurvey', 'EmpSatisfaction',
    'SpecialProjectsCount', 'LastPerformanceReview_Date',
    'DaysLateLast30', 'Absences'
]

DATE_COLS = ['DOB', 'DateofHire', 'DateofTermination', 'LastPerformanceReview_Date']

def extract() -> pd.DataFrame:
    """Extrait le fichier CSV, nettoie les chaînes et les dates."""
    logger.info(f"Lecture du fichier : {CSV_PATH}")

    # 1. Lecture du fichier
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        logger.debug(f"Fichier lu : {len(df)} lignes brutes")
    except FileNotFoundError:
        logger.critical(f"Fichier introuvable : {CSV_PATH}")
        raise
    except UnicodeDecodeError as e:
        logger.error(f"Erreur d'encodage lors de la lecture : {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la lecture du CSV : {e}")
        raise

    # 2. Validation des colonnes
    try:
        missing = set(EXPECTED_COLS) - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes : {missing}")
        logger.success(f"Toutes les colonnes attendues sont présentes ({len(df.columns)})")
    except ValueError as e:
        logger.error(f"Validation des colonnes échouée : {e}")
        raise

    # 3. Nettoyage des chaînes
    try:
        str_cols = df.select_dtypes(include=['object']).columns
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
        df['Sex'] = df['Sex'].str.upper()
        df['HispanicLatino'] = df['HispanicLatino'].str.capitalize()
        df['TermReason'] = df['TermReason'].fillna('')
        df['Department'] = df['Department'].str.strip()
        df['Position'] = df['Position'].str.strip()
        df['ManagerName'] = df['ManagerName'].str.strip()
        logger.debug("Nettoyage des chaînes terminé")
    except KeyError as e:
        logger.error(f"Colonne absente lors du nettoyage des chaînes : {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des chaînes : {e}")
        raise

    # 4. Conversion des dates
    try:
        for col in DATE_COLS:
            before = df[col].isna().sum()
            df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
            invalid = df[col].isna().sum() - before
            if invalid > 0:
                logger.warning(f"{col} : {invalid} dates invalides converties en NaT")
        logger.debug("Conversion des dates terminée")
    except Exception as e:
        logger.error(f"Erreur lors de la conversion des dates : {e}")
        raise

    # 5. Vérification des types et valeurs aberrantes
    numeric_cols = ['Salary', 'EngagementSurvey', 'EmpSatisfaction',
                    'SpecialProjectsCount', 'DaysLateLast30', 'Absences']
    for col in numeric_cols:
        if col not in df.columns:
            continue
        try:
            if df[col].dtype not in ['int64', 'float64']:
                logger.warning(f"{col} n'est pas numérique ({df[col].dtype}) – conversion forcée")
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if col == 'Salary':
                neg = (df[col] < 0).sum()
                if neg > 0:
                    logger.warning(f"{col} : {neg} valeurs négatives détectées")
            if col in ['EngagementSurvey', 'EmpSatisfaction']:
                out_of_range = df[col].notna() & ((df[col] < 1) | (df[col] > 5))
                if out_of_range.any():
                    logger.warning(f"{col} : {out_of_range.sum()} valeurs hors [1,5]")
            if col in ['Absences', 'DaysLateLast30']:
                neg = (df[col] < 0).sum()
                if neg > 0:
                    logger.warning(f"{col} : {neg} valeurs négatives détectées")
        except Exception as e:
            logger.error(f"Erreur lors de la validation de la colonne '{col}' : {e}")
            raise

    # 6. Rapport d'extraction
    try:
        logger.success(f"Extraction OK — {len(df)} lignes, {len(df.columns)} colonnes")
        logger.info(f"  DateofHire     : {df['DateofHire'].min().date()} → {df['DateofHire'].max().date()}")
        logger.info(f"  Termd=1 (partis)  : {df['Termd'].sum()}")
        logger.info(f"  Termd=0 (actifs)  : {(df['Termd']==0).sum()}")
        logger.info(f"  ManagerID nulls   : {df['ManagerID'].isnull().sum()}")
        logger.info(f"  DateofTermination nulls : {df['DateofTermination'].isnull().sum()}")
    except Exception as e:
        logger.warning(f"Impossible de générer le rapport complet : {e}")

    return df


if __name__ == "__main__":
    extract()