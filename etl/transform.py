import pandas as pd
from loguru import logger
from etl.dim_date import date_to_key

# ================================================================
#  Tables de référence (inchangées)
# ================================================================
RECRUITMENT_CATEGORIES = {
    'LinkedIn':                  'Digital',
    'Indeed':                    'Digital',
    'Google Search':             'Digital',
    'Website':                   'Digital',
    'CareerBuilder':             'Digital',
    'Monster':                   'Digital',
    'On-line Web application':   'Digital',
    'Employee Referral':         'Referral',
    'Diversity Job Fair':        'Event',
    'Professional Society':      'Event',
    'Information Session':       'Event',
    'Other':                     'Direct',
}

TERMINATION_MAP = {
    'n/a-stillemployed':                 ('Still Active', False),
    'still active':                      ('Still Active', False),
    'another position':                  ('Voluntary',    True),
    'unhappy':                           ('Voluntary',    True),
    'more money':                        ('Voluntary',    True),
    'career change':                     ('Voluntary',    True),
    'hours':                             ('Voluntary',    True),
    'return to school':                  ('Voluntary',    True),
    'relocation out of area':            ('Voluntary',    True),
    'family':                            ('Voluntary',    True),
    'medical issues':                    ('Voluntary',    True),
    'maternity leave - did not return':  ('Voluntary',    True),
    'military':                          ('Voluntary',    True),
    'retiring':                          ('Retirement',   True),
    'fired':                             ('Involuntary',  False),
    'attendance':                        ('Involuntary',  False),
    'performance':                       ('Involuntary',  False),
    'gross misconduct':                  ('Involuntary',  False),
    'no-call, no-show':                  ('Involuntary',  False),
}

# ================================================================
#  Dimensions
# ================================================================

def build_dim_employee(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit la dimension employé à partir des données brutes.
    Vérifie l'unicité de emp_id.
    """
    try:
        cols = ['EmpID', 'Employee_Name', 'DOB', 'Sex', 'GenderID',
                'MaritalDesc', 'MaritalStatusID', 'MarriedID',
                'CitizenDesc', 'HispanicLatino', 'RaceDesc', 'State', 'Zip']
        dim = df[cols].drop_duplicates(subset='EmpID').copy()
    except KeyError as e:
        logger.error(f"dim_employee — colonne manquante : {e}")
        raise

    try:
        dim = dim.rename(columns={
            'EmpID':           'emp_id',
            'Employee_Name':   'employee_name',
            'DOB':             'dob',
            'Sex':             'sex',
            'GenderID':        'gender_id',
            'MaritalDesc':     'marital_desc',
            'MaritalStatusID': 'marital_status_id',
            'MarriedID':       'married_id',
            'CitizenDesc':     'citizen_desc',
            'HispanicLatino':  'hispanic_latino',
            'RaceDesc':        'race_desc',
            'State':           'state',
            'Zip':             'zip',
        })

        # Conversion sécurisée de hispanic_latino
        mapping = {'yes': True, 'no': False, 'true': True, 'false': False}
        dim['hispanic_latino'] = dim['hispanic_latino'].str.lower().map(mapping).fillna(False)

        # Gestion des NaN dans le code postal
        dim['zip'] = dim['zip'].astype(str).str.strip().replace('nan', '')
    except Exception as e:
        logger.error(f"dim_employee — erreur lors du nettoyage/renommage : {e}")
        raise

    try:
        if dim['emp_id'].duplicated().any():
            logger.error("Doublons dans emp_id après déduplication !")
            raise ValueError("Doublons dans emp_id")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"dim_employee — erreur lors de la vérification d'unicité : {e}")
        raise

    dim = dim.sort_values('emp_id').reset_index(drop=True)
    dim.index += 1
    dim.index.name = 'employee_key'
    logger.success(f"dim_employee — {len(dim)} lignes")
    return dim.reset_index()


def build_dim_job(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit la dimension job (poste, département, statut).
    Vérifie l'unicité de la combinaison (position_id, dept_id, emp_status_id).
    """
    try:
        cols = ['PositionID', 'Position', 'Department', 'DeptID',
                'EmploymentStatus', 'EmpStatusID', 'FromDiversityJobFairID']
        dim = df[cols].drop_duplicates(
            subset=['PositionID', 'DeptID', 'EmpStatusID']
        ).copy()
    except KeyError as e:
        logger.error(f"dim_job — colonne manquante : {e}")
        raise

    try:
        dim = dim.rename(columns={
            'PositionID':             'position_id',
            'Position':               'position',
            'Department':             'department',
            'DeptID':                 'dept_id',
            'EmploymentStatus':       'employment_status',
            'EmpStatusID':            'emp_status_id',
            'FromDiversityJobFairID': 'from_diversity_fair',
        })
        dim['from_diversity_fair'] = dim['from_diversity_fair'].astype(bool)
    except Exception as e:
        logger.error(f"dim_job — erreur lors du renommage/cast : {e}")
        raise

    try:
        if dim.duplicated(subset=['position_id', 'dept_id', 'emp_status_id']).any():
            logger.error("Doublons dans (position_id, dept_id, emp_status_id) après déduplication !")
            raise ValueError("Doublons dans dim_job")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"dim_job — erreur lors de la vérification d'unicité : {e}")
        raise

    dim = dim.sort_values('position_id').reset_index(drop=True)
    dim.index += 1
    dim.index.name = 'job_key'
    logger.success(f"dim_job — {len(dim)} lignes")
    return dim.reset_index()


def build_dim_manager(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit la dimension manager, avec une sentinelle -1 pour les inconnus.
    """
    try:
        sentinel = pd.DataFrame([{
            'manager_key': -1,
            'manager_id':  -1,
            'manager_name': 'Manager inconnu'
        }])
        known = df[df['ManagerID'].notna()][['ManagerID', 'ManagerName']] \
                  .drop_duplicates(subset='ManagerID') \
                  .rename(columns={'ManagerID': 'manager_id',
                                   'ManagerName': 'manager_name'})
        known['manager_id'] = known['manager_id'].astype(int)
    except KeyError as e:
        logger.error(f"dim_manager — colonne manquante : {e}")
        raise
    except Exception as e:
        logger.error(f"dim_manager — erreur lors de la construction : {e}")
        raise

    try:
        if known['manager_id'].duplicated().any():
            logger.error("Doublons dans manager_id")
            raise ValueError("Doublons dans manager_id")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"dim_manager — erreur lors de la vérification d'unicité : {e}")
        raise

    known = known.sort_values('manager_id').reset_index(drop=True)
    known.index += 1
    known.index.name = 'manager_key'
    known = known.reset_index()
    dim = pd.concat([sentinel, known], ignore_index=True)
    logger.success(f"dim_manager — {len(dim)} lignes (dont sentinelle -1)")
    return dim


def build_dim_recruitment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit la dimension source de recrutement.
    """
    try:
        sources = sorted(df['RecruitmentSource'].dropna().unique())
        rows = [
            {
                'recruitment_source': s,
                'source_category': RECRUITMENT_CATEGORIES.get(s, 'Direct')
            }
            for s in sources
        ]
        dim = pd.DataFrame(rows).reset_index(drop=True)
        dim.index += 1
        dim.index.name = 'recruitment_key'
    except KeyError as e:
        logger.error(f"dim_recruitment — colonne manquante : {e}")
        raise
    except Exception as e:
        logger.error(f"dim_recruitment — erreur lors de la construction : {e}")
        raise

    logger.success(f"dim_recruitment — {len(dim)} lignes")
    return dim.reset_index()


def build_dim_termination(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit la dimension motif de départ.
    Vérifie que toutes les raisons sont mappées (avec fallback).
    """
    try:
        reasons = df['TermReason'].fillna('Still Active').str.strip().unique()
    except KeyError as e:
        logger.error(f"dim_termination — colonne manquante : {e}")
        raise

    try:
        rows = []
        seen = set()
        rows.append({'term_reason': 'Still Active',
                     'term_category': 'Still Active', 'is_voluntary': False})
        seen.add('still active')
        missing_categories = []
        for r in sorted(reasons):
            norm = r.strip().lower()
            if norm in seen or norm in ('n/a-stillemployed', ''):
                continue
            cat, vol = TERMINATION_MAP.get(norm, (None, None))
            if cat is None:
                missing_categories.append(r)
                cat, vol = 'Voluntary', True  # fallback
            rows.append({'term_reason': r.strip(),
                         'term_category': cat, 'is_voluntary': vol})
            seen.add(norm)
        if missing_categories:
            logger.warning(f"Raisons non mappées dans TERMINATION_MAP (fallback appliqué) : {missing_categories}")
        dim = pd.DataFrame(rows).reset_index(drop=True)
        dim.index += 1
        dim.index.name = 'termination_key'
    except Exception as e:
        logger.error(f"dim_termination — erreur lors de la construction : {e}")
        raise

    logger.success(f"dim_termination — {len(dim)} lignes")
    return dim.reset_index()


DIM_PERFORMANCE = pd.DataFrame([
    {'performance_key': 1, 'perf_score_id': 1,
     'performance_score': 'PIP',               'performance_label': 'En amélioration', 'performance_rank': 1},
    {'performance_key': 2, 'perf_score_id': 2,
     'performance_score': 'Needs Improvement', 'performance_label': 'À améliorer',     'performance_rank': 2},
    {'performance_key': 3, 'perf_score_id': 3,
     'performance_score': 'Fully Meets',       'performance_label': 'Satisfaisant',    'performance_rank': 3},
    {'performance_key': 4, 'perf_score_id': 4,
     'performance_score': 'Exceeds',           'performance_label': 'Exceptionnel',    'performance_rank': 4},
])

# ================================================================
#  Table de faits
# ================================================================

SNAPSHOT_DATE = pd.Timestamp.today().normalize()

def build_fact(
    df:               pd.DataFrame,
    dim_employee:     pd.DataFrame,
    dim_job:          pd.DataFrame,
    dim_manager:      pd.DataFrame,
    dim_recruitment:  pd.DataFrame,
    dim_termination:  pd.DataFrame,
    dim_performance:  pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit la table de faits d'attrition.
    Calcule tenure, délai depuis dernière évaluation, et gère les outliers.
    Vérifie l'intégrité référentielle.
    """
    fact = df.copy()
    logger.info(f"Snapshot date utilisée pour les calculs : {SNAPSHOT_DATE.date()}")

    # ── Mesures calculées ─────────────────────────────────────────
    try:
        fact['attrition_flag'] = fact['Termd'].astype(int)
        fact['tenure_days'] = (
            (fact['DateofTermination'] - fact['DateofHire']).dt.days
            .fillna((SNAPSHOT_DATE - fact['DateofHire']).dt.days)
        )
        fact['days_since_last_review'] = (
            SNAPSHOT_DATE - fact['LastPerformanceReview_Date']
        ).dt.days.where(fact['LastPerformanceReview_Date'].notna())
        logger.debug("Mesures calculées (attrition_flag, tenure_days, days_since_last_review)")
    except KeyError as e:
        logger.error(f"build_fact — colonne manquante pour les mesures calculées : {e}")
        raise
    except Exception as e:
        logger.error(f"build_fact — erreur lors du calcul des mesures : {e}")
        raise

    # ── Clés dates ────────────────────────────────────────────────
    try:
        fact['hire_date_key']        = date_to_key(fact['DateofHire'])
        fact['departure_date_key']   = date_to_key(fact['DateofTermination'],         null_key=-1)
        fact['last_review_date_key'] = date_to_key(fact['LastPerformanceReview_Date'], null_key=-1)
        logger.debug("Clés dates générées")
    except Exception as e:
        logger.error(f"build_fact — erreur lors de la génération des clés dates : {e}")
        raise

    # ── Validation des mesures ────────────────────────────────────
    if (fact['Salary'] < 0).any():
        logger.warning("Salaire négatif détecté")
    if (fact['EngagementSurvey'] < 1).any() or (fact['EngagementSurvey'] > 5).any():
        logger.warning("EngagementSurvey hors plage [1,5]")
    if (fact['EmpSatisfaction'] < 1).any() or (fact['EmpSatisfaction'] > 5).any():
        logger.warning("EmpSatisfaction hors plage [1,5]")
    if (fact['Absences'] < 0).any():
        logger.warning("Absences négatives détectées")
    if (fact['DaysLateLast30'] < 0).any():
        logger.warning("DaysLateLast30 négatives détectées")

    # ── Jointures avec les dimensions ────────────────────────────
    try:
        fact = fact.merge(
            dim_employee[['employee_key', 'emp_id']].rename(columns={'emp_id': 'EmpID'}),
            on='EmpID', how='left'
        )
        fact = fact.merge(
            dim_job[['job_key', 'position_id', 'dept_id', 'emp_status_id']]
                   .rename(columns={'position_id': 'PositionID',
                                    'dept_id': 'DeptID',
                                    'emp_status_id': 'EmpStatusID'}),
            on=['PositionID', 'DeptID', 'EmpStatusID'], how='left'
        )
        fact['ManagerID_int'] = fact['ManagerID'].fillna(-1).astype(int)
        fact = fact.merge(
            dim_manager[['manager_key', 'manager_id']]
                       .rename(columns={'manager_id': 'ManagerID_int'}),
            on='ManagerID_int', how='left'
        )
        fact['manager_key'] = fact['manager_key'].fillna(-1).astype(int)
        fact = fact.merge(
            dim_recruitment[['recruitment_key', 'recruitment_source']]
                           .rename(columns={'recruitment_source': 'RecruitmentSource'}),
            on='RecruitmentSource', how='left'
        )
        fact['TermReason_norm'] = fact['TermReason'].fillna('Still Active').str.strip()
        fact['TermReason_norm'] = fact['TermReason_norm'].replace('N/A-StillEmployed', 'Still Active')
        fact = fact.merge(
            dim_termination[['termination_key', 'term_reason']]
                           .rename(columns={'term_reason': 'TermReason_norm'}),
            on='TermReason_norm', how='left'
        )
        fact['termination_key'] = fact['termination_key'].fillna(1).astype(int)
        fact = fact.merge(
            dim_performance[['performance_key', 'perf_score_id']]
                           .rename(columns={'perf_score_id': 'PerfScoreID'}),
            on='PerfScoreID', how='left'
        )
        logger.debug("Jointures avec toutes les dimensions effectuées")
    except KeyError as e:
        logger.error(f"build_fact — clé manquante lors d'une jointure : {e}")
        raise
    except Exception as e:
        logger.error(f"build_fact — erreur lors des jointures : {e}")
        raise

    # ── Vérification des clés étrangères ─────────────────────────
    try:
        fk_cols = ['employee_key', 'job_key', 'manager_key',
                   'recruitment_key', 'termination_key', 'performance_key',
                   'hire_date_key']
        for fk in fk_cols:
            n = fact[fk].isnull().sum()
            if n > 0:
                logger.error(f"FK NULLE : {fk} — {n} lignes non résolues !")
                raise ValueError(f"Intégrité référentielle violée : {fk} contient {n} valeurs nulles")
        logger.success("Toutes les FK sont résolues — aucun null détecté")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"build_fact — erreur lors de la vérification des FK : {e}")
        raise

    # ── Sélection et renommage des colonnes finales ───────────────
    try:
        fact_final = fact[[
            'employee_key', 'job_key', 'manager_key',
            'recruitment_key', 'termination_key', 'performance_key',
            'hire_date_key', 'departure_date_key', 'last_review_date_key',
            'attrition_flag', 'tenure_days', 'days_since_last_review',
            'Salary', 'EngagementSurvey', 'EmpSatisfaction',
            'SpecialProjectsCount', 'DaysLateLast30', 'Absences',
        ]].rename(columns={
            'Salary':              'salary',
            'EngagementSurvey':    'engagement_survey',
            'EmpSatisfaction':     'emp_satisfaction',
            'SpecialProjectsCount':'special_projects_count',
            'DaysLateLast30':      'days_late_last_30',
            'Absences':            'absences',
        })
        # Gestion des outliers
        fact_final.loc[(fact_final['engagement_survey'] < 1) | (fact_final['engagement_survey'] > 5),
                       'engagement_survey'] = None
        fact_final.loc[(fact_final['emp_satisfaction'] < 1) | (fact_final['emp_satisfaction'] > 5),
                       'emp_satisfaction'] = None
        fact_final.loc[fact_final['days_late_last_30'] < 0, 'days_late_last_30'] = 0
        fact_final.loc[fact_final['absences'] < 0, 'absences'] = 0
    except KeyError as e:
        logger.error(f"build_fact — colonne manquante lors de la sélection finale : {e}")
        raise
    except Exception as e:
        logger.error(f"build_fact — erreur lors de la sélection/nettoyage final : {e}")
        raise

    # ── Rapport final ─────────────────────────────────────────────
    try:
        logger.success(f"fact_employee_attrition — {len(fact_final)} lignes")
        logger.info(f"  Attrition flag=1  : {fact_final['attrition_flag'].sum()}")
        logger.info(f"  Actifs flag=0     : {(fact_final['attrition_flag']==0).sum()}")
        logger.info(f"  Tenure moyen (partis) : "
                    f"{fact_final.loc[fact_final['attrition_flag']==1,'tenure_days'].mean():.0f} jours")
        logger.info(f"  Salaire moyen     : {fact_final['salary'].mean():,.0f} $/an")
    except Exception as e:
        logger.warning(f"Impossible de générer le rapport complet : {e}")

    return fact_final


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from etl.extract import extract

    logger.info("=== Lancement du test de la transformation ===")
    df_raw = extract()

    dim_employee    = build_dim_employee(df_raw)
    dim_job         = build_dim_job(df_raw)
    dim_manager     = build_dim_manager(df_raw)
    dim_recruitment = build_dim_recruitment(df_raw)
    dim_termination = build_dim_termination(df_raw)

    fact = build_fact(
        df_raw,
        dim_employee, dim_job, dim_manager,
        dim_recruitment, dim_termination, DIM_PERFORMANCE
    )
    logger.success("=== Test terminé avec succès ===")