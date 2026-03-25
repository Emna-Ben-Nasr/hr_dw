import pandas as pd
from loguru import logger
from config import CSV_PATH

# Colonnes attendues dans HRDataset v14
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

DATE_COLS = ['DOB', 'DateofHire', 'DateofTermination',
             'LastPerformanceReview_Date']


def extract() -> pd.DataFrame:
    logger.info(f"Lecture du fichier : {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, encoding='utf-8')

    # ── Validation des colonnes ───────────────────────────────────
    missing = set(EXPECTED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")
    logger.success(f"Toutes les colonnes attendues sont présentes ({len(df.columns)})")

    # ── Nettoyage des espaces parasites (audit v14) ───────────────
    df['Department']     = df['Department'].str.strip()
    df['Sex']            = df['Sex'].str.strip().str.upper()
    df['HispanicLatino'] = df['HispanicLatino'].str.strip().str.capitalize()
    df['TermReason']     = df['TermReason'].str.strip()
    df['Position']       = df['Position'].str.strip()
    df['ManagerName']    = df['ManagerName'].str.strip()

    # ── Parse des dates ───────────────────────────────────────────
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')

    # ── Rapport d'extraction ──────────────────────────────────────
    logger.success(f"Extraction OK — {len(df)} lignes, {len(df.columns)} colonnes")
    logger.info(f"  DateofHire     : {df['DateofHire'].min().date()} → {df['DateofHire'].max().date()}")
    logger.info(f"  Termd=1 (partis)  : {df['Termd'].sum()}")
    logger.info(f"  Termd=0 (actifs)  : {(df['Termd']==0).sum()}")
    logger.info(f"  ManagerID nulls   : {df['ManagerID'].isnull().sum()}")
    logger.info(f"  DateofTermination nulls : {df['DateofTermination'].isnull().sum()}")

    return df
if __name__ == "__main__":
    try:
        logger.info("🚀 Lancement du script extract")
        df = extract()
        logger.success("✅ Script exécuté avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur : {e}")