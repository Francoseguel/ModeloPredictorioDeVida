import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# PhenoAge (Levine et al. 2018) — edad biologica a partir de 9 biomarcadores + edad
# -----------------------------------------------------------------------------
# Coeficientes y unidades del paper original (implementacion BioAge/phenoage).
# Nuestros datos vienen en unidades NHANES, asi que se convierten antes de aplicar
# la combinacion lineal. wbc ya esta en 1000 celulas/uL; mcv en fL; rdw y
# linfocitos en %; alp en U/L.
_PHENOAGE_COEF = {
    "albumina": -0.0336,        # g/L      (NHANES g/dL  -> *10)
    "creatinina": 0.0095,       # umol/L   (NHANES mg/dL -> *88.4017)
    "glucosa_serica": 0.1953,   # mmol/L   (NHANES mg/dL -> *0.0555)
    "crp_ln": 0.0954,           # ln(mg/dL)(NHANES mg/L  -> /10 -> ln)
    "linfocitos_pct": -0.0120,  # %
    "mcv": 0.0268,              # fL
    "rdw": 0.3306,              # %
    "alp": 0.00188,             # U/L
    "wbc": 0.0554,              # 1000/uL
    "edad": 0.0804,             # años
}
_PHENOAGE_INTERCEPT = -19.9067


def _phenoage(bio: pd.DataFrame, edad: pd.Series) -> pd.Series:
    # Combina los 9 biomarcadores (convertidos a las unidades de Levine) con la
    # edad cronologica y devuelve la edad fenotipica (PhenoAge) en años.
    df = bio.copy()
    alb = df["albumina"] * 10.0
    cre = df["creatinina"] * 88.4017
    glu = df["glucosa_serica"] * 0.0555
    crp_ln = np.log(np.clip(df["crp"] / 10.0, 1e-4, None))

    xb = (
        _PHENOAGE_INTERCEPT
        + _PHENOAGE_COEF["albumina"] * alb
        + _PHENOAGE_COEF["creatinina"] * cre
        + _PHENOAGE_COEF["glucosa_serica"] * glu
        + _PHENOAGE_COEF["crp_ln"] * crp_ln
        + _PHENOAGE_COEF["linfocitos_pct"] * df["linfocitos_pct"]
        + _PHENOAGE_COEF["mcv"] * df["mcv"]
        + _PHENOAGE_COEF["rdw"] * df["rdw"]
        + _PHENOAGE_COEF["alp"] * df["alp"]
        + _PHENOAGE_COEF["wbc"] * df["wbc"]
        + _PHENOAGE_COEF["edad"] * edad
    )

    # Mortalidad a 10 años (modelo de Gompertz del paper) y conversion a edad.
    g = 0.0076927
    mort = 1.0 - np.exp(-np.exp(xb) * (np.exp(120.0 * g) - 1.0) / g)
    mort = np.clip(mort, 1e-8, 1 - 1e-8)
    phenoage = 141.50225 + np.log(-0.00553 * np.log(1.0 - mort)) / 0.090165
    return phenoage


def create_target(target_raw: pd.DataFrame, params: dict, demo: pd.DataFrame = None) -> pd.DataFrame:
    # Deriva el target de regresion (y_reg) y de clasificacion (y_clf) a partir
    # de las columnas reservadas en *_target_raw. Config en params['target']:
    #   - type: 'column' (default) | 'phenoage'
    #   - reg: columna de target_raw para regresion (modo column)
    #   - clf_from / clf_threshold: binariza clf = (col >= threshold)
    #   Para phenoage: usa los 9 biomarcadores + edad de demo; clf = aceleracion
    #   (PhenoAge - edad cronologica > 0 -> envejecimiento acelerado).
    cfg = params.get("target") or {}
    ttype = cfg.get("type", "column")

    if ttype == "phenoage":
        if demo is None:
            raise ValueError("create_target phenoage requiere 'demo' (edad cronologica).")
        edad = demo["edad"].reindex(target_raw.index)
        bio = target_raw.dropna()
        edad = edad.loc[bio.index].dropna()
        bio = bio.loc[edad.index]
        y_reg = _phenoage(bio, edad).rename("y_reg")
        accel = (y_reg - edad)
        y_clf = (accel > 0).astype(int).rename("y_clf")
        out = pd.concat([y_reg, y_clf], axis=1)
        logger.info("PhenoAge: n=%d | media=%.1f años | aceleracion media=%.2f | %%acelerados=%.1f",
                    len(out), y_reg.mean(), accel.mean(), 100 * y_clf.mean())
    else:
        reg_col = cfg["reg"]
        clf_from = cfg.get("clf_from", reg_col)
        thr = cfg["clf_threshold"]
        df = target_raw.copy()
        y_reg = df[reg_col].rename("y_reg")
        y_clf = (df[clf_from] >= thr).astype("float")
        # filas sin valor de origen para clf -> NaN (se descartan luego)
        y_clf = y_clf.where(df[clf_from].notna()).rename("y_clf")
        out = pd.concat([y_reg, y_clf], axis=1).dropna()
        out["y_clf"] = out["y_clf"].astype(int)
        logger.info("Target '%s': n=%d | y_reg media=%.2f | %%clf+=%.1f",
                    cfg.get("clf_name", reg_col), len(out), out["y_reg"].mean(),
                    100 * out["y_clf"].mean())

    return out


def split_dataset(X: pd.DataFrame, target: pd.DataFrame, params: dict) -> tuple:
    # Split unico estratificado por el target de clasificacion (sirve para clf y
    # reg: mismas filas en train/test, alineadas por SEQN). Solo se usan las filas
    # que tienen features Y target (inner join por indice).
    test_size = params.get("test_size", 0.2)
    rs = params.get("random_state", 42)

    common = X.index.intersection(target.index)
    Xc = X.loc[common]
    y_clf = target.loc[common, "y_clf"]
    y_reg = target.loc[common, "y_reg"]

    strat = y_clf if y_clf.nunique() > 1 else None
    X_train, X_test, ytr_clf, yte_clf = train_test_split(
        Xc, y_clf, test_size=test_size, random_state=rs, stratify=strat,
    )
    ytr_reg = y_reg.loc[ytr_clf.index]
    yte_reg = y_reg.loc[yte_clf.index]

    logger.info("Split: train=%d test=%d | clf pos_rate train=%.3f test=%.3f",
                len(X_train), len(X_test), ytr_clf.mean(), yte_clf.mean())

    return (
        X_train, X_test,
        ytr_clf.to_frame(), yte_clf.to_frame(),
        ytr_reg.to_frame(), yte_reg.to_frame(),
    )
