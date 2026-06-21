import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import (
    ElasticNet, LinearRegression, LogisticRegression, Ridge,
)
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error,
    mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

logger = logging.getLogger(__name__)
MODELS_DIR = Path(__file__).parents[4] / "models" / "trained_models"


def _build_classifiers(params: dict, rs: int) -> dict:
    # 6 clasificadores de distintas familias (lineal, probabilistico, distancias,
    # arbol, ensemble, kernel) para comparar cual se adapta mejor a cada dataset.
    dtc = params.get("clf_decision_tree", {})
    gnb = params.get("clf_gaussian_nb", {})
    knc = params.get("clf_knn", {})
    lrc = params.get("clf_logistic_regression", {})
    rfc = params.get("clf_random_forest", {})
    svc = params.get("clf_svc", {})
    return {
        "DecisionTree": Pipeline([("clf", DecisionTreeClassifier(
            criterion=dtc.get("criterion", "gini"),
            splitter=dtc.get("splitter", "best"),
            max_depth=dtc.get("max_depth"),
            min_samples_split=dtc.get("min_samples_split", 2),
            min_samples_leaf=dtc.get("min_samples_leaf", 1),
            max_features=dtc.get("max_features"),
            class_weight=dtc.get("class_weight"),
            ccp_alpha=dtc.get("ccp_alpha", 0.0),
            random_state=rs,
        ))]),
        "GaussianNB": Pipeline([("clf", GaussianNB(
            var_smoothing=gnb.get("var_smoothing", 1e-9),
        ))]),
        "KNN": Pipeline([("clf", KNeighborsClassifier(
            n_neighbors=knc.get("n_neighbors", 5),
            weights=knc.get("weights", "uniform"),
            algorithm=knc.get("algorithm", "auto"),
            p=knc.get("p", 2),
            metric=knc.get("metric", "minkowski"),
        ))]),
        "LogisticRegression": Pipeline([("clf", LogisticRegression(
            penalty=lrc.get("penalty", "l2"),
            C=lrc.get("C", 1.0),
            solver=lrc.get("solver", "lbfgs"),
            max_iter=lrc.get("max_iter", 1000),
            class_weight=lrc.get("class_weight"),
            random_state=rs,
        ))]),
        "RandomForest": Pipeline([("clf", RandomForestClassifier(
            n_estimators=rfc.get("n_estimators", 100),
            criterion=rfc.get("criterion", "gini"),
            max_depth=rfc.get("max_depth"),
            min_samples_split=rfc.get("min_samples_split", 2),
            min_samples_leaf=rfc.get("min_samples_leaf", 1),
            max_features=rfc.get("max_features", "sqrt"),
            bootstrap=rfc.get("bootstrap", True),
            class_weight=rfc.get("class_weight"),
            ccp_alpha=rfc.get("ccp_alpha", 0.0),
            n_jobs=-1, random_state=rs,
        ))]),
        "SVC": Pipeline([("clf", SVC(
            C=svc.get("C", 1.0),
            kernel=svc.get("kernel", "rbf"),
            gamma=svc.get("gamma", "scale"),
            degree=svc.get("degree", 3),
            class_weight=svc.get("class_weight", "balanced"),
            probability=True, random_state=rs,
        ))]),
    }


def _build_regressors(params: dict, rs: int) -> dict:
    # 6 regresores (lineal baseline, polinomico, arbol, distancias, ensemble, kernel).
    dtc = params.get("reg_decision_tree", {})
    knc = params.get("reg_knn", {})
    rfc = params.get("reg_random_forest", {})
    svr = params.get("reg_svr", {})
    poly_deg = params.get("reg_polynomial_degree", 2)
    return {
        "LinearRegression": Pipeline([("reg", LinearRegression(fit_intercept=True))]),
        "PolynomialRegression": Pipeline([
            ("poly", PolynomialFeatures(degree=poly_deg, include_bias=True, interaction_only=False)),
            ("reg", LinearRegression(fit_intercept=True)),
        ]),
        "DecisionTree": Pipeline([("reg", DecisionTreeRegressor(
            criterion=dtc.get("criterion", "squared_error"),
            splitter=dtc.get("splitter", "best"),
            max_depth=dtc.get("max_depth"),
            min_samples_split=dtc.get("min_samples_split", 2),
            min_samples_leaf=dtc.get("min_samples_leaf", 1),
            ccp_alpha=dtc.get("ccp_alpha", 0.0),
            random_state=rs,
        ))]),
        "KNN": Pipeline([("reg", KNeighborsRegressor(
            n_neighbors=knc.get("n_neighbors", 5),
            weights=knc.get("weights", "uniform"),
            algorithm=knc.get("algorithm", "auto"),
            p=knc.get("p", 2),
        ))]),
        "RandomForest": Pipeline([("reg", RandomForestRegressor(
            n_estimators=rfc.get("n_estimators", 100),
            criterion=rfc.get("criterion", "squared_error"),
            max_depth=rfc.get("max_depth"),
            min_samples_split=rfc.get("min_samples_split", 2),
            min_samples_leaf=rfc.get("min_samples_leaf", 1),
            max_features=rfc.get("max_features", 1.0),
            bootstrap=rfc.get("bootstrap", True),
            ccp_alpha=rfc.get("ccp_alpha", 0.0),
            n_jobs=-1, random_state=rs,
        ))]),
        "SVR": Pipeline([("reg", SVR(
            kernel=svr.get("kernel", "rbf"),
            gamma=svr.get("gamma", "scale"),
            C=svr.get("C", 1.0),
            epsilon=svr.get("epsilon", 0.1),
            degree=svr.get("degree", 3),
        ))]),
    }


def train_classifiers(X_train, y_train, X_test, y_test, params, ds_name):
    # Entrena los 6 clasificadores y devuelve una tabla comparativa. F1 y ROC-AUC
    # como metricas principales (los targets suelen estar desbalanceados). Guarda
    # cada modelo en models/trained_models/{ds}_{modelo}_clf.joblib.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    y_tr, y_te = y_train.squeeze(), y_test.squeeze()
    rs = params.get("random_state", 42)
    rows = []
    for name, pipe in _build_classifiers(params, rs).items():
        pipe.fit(X_train, y_tr)
        y_pred = pipe.predict(X_test)
        y_prob = pipe.predict_proba(X_test)[:, 1]
        rows.append({
            "Modelo": name,
            "Accuracy": round(accuracy_score(y_te, y_pred), 4),
            "F1": round(f1_score(y_te, y_pred, zero_division=0), 4),
            "Precision": round(precision_score(y_te, y_pred, zero_division=0), 4),
            "Recall": round(recall_score(y_te, y_pred, zero_division=0), 4),
            "ROC_AUC": round(roc_auc_score(y_te, y_prob), 4),
        })
        joblib.dump(pipe, MODELS_DIR / f"{ds_name}_{name.lower()}_clf.joblib")
    report = pd.DataFrame(rows).sort_values("F1", ascending=False).reset_index(drop=True)
    logger.info("[%s] clf — mejor por F1: %s (%.4f)", ds_name,
                report.iloc[0]["Modelo"], report.iloc[0]["F1"])
    return report


def train_regressors(X_train, y_train, X_test, y_test, params, ds_name):
    # Entrena los regresores y devuelve una tabla comparativa. MAE (mismas unidades
    # que el target) como metrica principal; R2 y RMSE complementan.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    y_tr, y_te = y_train.squeeze(), y_test.squeeze()
    rs = params.get("random_state", 42)
    rows = []
    for name, pipe in _build_regressors(params, rs).items():
        pipe.fit(X_train, y_tr)
        y_pred = pipe.predict(X_test)
        rows.append({
            "Modelo": name,
            "R2": round(r2_score(y_te, y_pred), 4),
            "MAE": round(mean_absolute_error(y_te, y_pred), 4),
            "RMSE": round(float(np.sqrt(mean_squared_error(y_te, y_pred))), 4),
        })
        joblib.dump(pipe, MODELS_DIR / f"{ds_name}_{name.lower()}_reg.joblib")
    report = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
    logger.info("[%s] reg — mejor por MAE: %s (%.4f)", ds_name,
                report.iloc[0]["Modelo"], report.iloc[0]["MAE"])
    return report


# =============================================================================
# TUNING DE HIPERPARAMETROS (RandomizedSearchCV)
# -----------------------------------------------------------------------------
# Espacios de busqueda definidos en codigo (junto a los estimadores), gobernados
# por cv_folds / rs_n_iter / random_state de params:modeling. X ya viene escalado,
# imputado y encodeado de data_transformation (ajustado SOLO con train), asi que
# los estimadores van "pelados" dentro de un Pipeline de 1 paso (clave de paso
# "clf"/"reg") para que los modelos guardados sean consistentes con el resto.
# Distribuciones continuas (loguniform/randint de scipy) para C/gamma/alpha/...;
# listas para opciones discretas. Scoring: F1 (clf) y neg-MAE (reg).
# =============================================================================


def _grid_size(dist: dict) -> float:
    # Combinaciones de un espacio puramente discreto (para no pedir a Randomized
    # mas iteraciones que combinaciones posibles -> ValueError). Si algun valor es
    # una distribucion de scipy (tiene .rvs) el espacio es continuo -> infinito.
    n = 1
    for v in dist.values():
        if hasattr(v, "rvs"):
            return float("inf")
        n *= len(v)
    return n


def _clf_search_spaces(rs: int) -> dict:
    # 6 clasificadores con su rejilla de busqueda. GaussianNB usa var_smoothing
    # continuo; el resto mezcla continuo (C/gamma) y discreto (profundidades, k...).
    return {
        "DecisionTree": (
            Pipeline([("clf", DecisionTreeClassifier(random_state=rs))]),
            {
                "clf__criterion": ["gini", "entropy"],
                "clf__max_depth": [3, 5, 8, 12, 20, None],
                "clf__min_samples_split": [2, 5, 10, 20],
                "clf__min_samples_leaf": [1, 2, 5, 10],
                "clf__class_weight": [None, "balanced"],
                "clf__ccp_alpha": loguniform(1e-4, 1e-1),
            },
        ),
        "GaussianNB": (
            Pipeline([("clf", GaussianNB())]),
            {"clf__var_smoothing": loguniform(1e-11, 1e-5)},
        ),
        "KNN": (
            Pipeline([("clf", KNeighborsClassifier())]),
            {
                "clf__n_neighbors": randint(3, 40),
                "clf__weights": ["uniform", "distance"],
                "clf__p": [1, 2],
            },
        ),
        "LogisticRegression": (
            Pipeline([("clf", LogisticRegression(
                solver="liblinear", max_iter=2000, random_state=rs))]),
            {
                "clf__C": loguniform(1e-3, 1e2),
                "clf__penalty": ["l1", "l2"],
                "clf__class_weight": [None, "balanced"],
            },
        ),
        "RandomForest": (
            Pipeline([("clf", RandomForestClassifier(
                n_jobs=-1, random_state=rs))]),
            {
                "clf__n_estimators": randint(100, 600),
                "clf__max_depth": [4, 8, 12, 20, None],
                "clf__min_samples_split": [2, 5, 10],
                "clf__min_samples_leaf": [1, 2, 4],
                "clf__max_features": ["sqrt", "log2", 0.5],
                "clf__class_weight": [None, "balanced"],
            },
        ),
        "SVC": (
            Pipeline([("clf", SVC(probability=True, random_state=rs))]),
            {
                "clf__C": loguniform(1e-2, 1e3),
                "clf__gamma": loguniform(1e-4, 1e1),
                "clf__kernel": ["rbf", "poly"],
                "clf__class_weight": [None, "balanced"],
            },
        ),
    }


def _reg_search_spaces(rs: int) -> dict:
    # LinearRegression no tiene hiperparametros -> se ajusta sin busqueda (queda
    # como baseline). Se anaden Ridge y ElasticNet (regularizacion = palanca natural
    # con 112 features) y la PolynomialRegression usa Ridge para no colapsar.
    return {
        "LinearRegression": (Pipeline([("reg", LinearRegression())]), {}),
        "Ridge": (
            Pipeline([("reg", Ridge(random_state=rs))]),
            {"reg__alpha": loguniform(1e-2, 1e3)},
        ),
        "ElasticNet": (
            Pipeline([("reg", ElasticNet(max_iter=5000, random_state=rs))]),
            {
                "reg__alpha": loguniform(1e-3, 1e1),
                "reg__l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9],
            },
        ),
        "PolynomialRegression": (
            Pipeline([
                ("poly", PolynomialFeatures(include_bias=False)),
                ("reg", Ridge(random_state=rs)),
            ]),
            {
                "poly__degree": [2],
                "poly__interaction_only": [True, False],
                "reg__alpha": loguniform(1e-1, 1e4),
            },
        ),
        "DecisionTree": (
            Pipeline([("reg", DecisionTreeRegressor(random_state=rs))]),
            {
                "reg__max_depth": [3, 5, 8, 12, 20, None],
                "reg__min_samples_split": [2, 5, 10, 20],
                "reg__min_samples_leaf": [1, 2, 5, 10],
                "reg__ccp_alpha": loguniform(1e-4, 1e-1),
            },
        ),
        "KNN": (
            Pipeline([("reg", KNeighborsRegressor())]),
            {
                "reg__n_neighbors": randint(3, 40),
                "reg__weights": ["uniform", "distance"],
                "reg__p": [1, 2],
            },
        ),
        "RandomForest": (
            Pipeline([("reg", RandomForestRegressor(n_jobs=-1, random_state=rs))]),
            {
                "reg__n_estimators": randint(100, 600),
                "reg__max_depth": [4, 8, 12, 20, None],
                "reg__min_samples_split": [2, 5, 10],
                "reg__min_samples_leaf": [1, 2, 4],
                "reg__max_features": ["sqrt", "log2", 0.5, 1.0],
            },
        ),
        "SVR": (
            Pipeline([("reg", SVR())]),
            {
                "reg__C": loguniform(1e-1, 1e3),
                "reg__gamma": loguniform(1e-4, 1e1),
                "reg__epsilon": loguniform(1e-2, 1e0),
                "reg__kernel": ["rbf", "poly"],
            },
        ),
    }


def _search(pipe, dist, X_train, y_tr, scoring, cv, n_iter, rs):
    # Ajusta el modelo: RandomizedSearchCV si hay espacio de busqueda, fit directo
    # si no (p.ej. LinearRegression). Devuelve (mejor_estimador, mejor_score_cv).
    if not dist:
        pipe.fit(X_train, y_tr)
        return pipe, float("nan")
    size = _grid_size(dist)
    n_eff = n_iter if size == float("inf") else min(n_iter, int(size))
    search = RandomizedSearchCV(
        pipe, dist, n_iter=n_eff, scoring=scoring, cv=cv,
        n_jobs=-1, random_state=rs, refit=True,
    )
    search.fit(X_train, y_tr)
    return search.best_estimator_, search.best_score_


def tune_classifiers(X_train, y_train, X_test, y_test, params, ds_name):
    # Tunea los 6 clasificadores con RandomizedSearchCV (scoring=F1, CV en train),
    # evalua el mejor de cada familia en test y guarda {ds}_{modelo}_clf_tuned.joblib.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    y_tr, y_te = y_train.squeeze(), y_test.squeeze()
    rs = params.get("random_state", 42)
    cv = params.get("cv_folds", 5)
    n_iter = params.get("rs_n_iter", 40)
    rows = []
    for name, (pipe, dist) in _clf_search_spaces(rs).items():
        best, cv_score = _search(pipe, dist, X_train, y_tr, "f1", cv, n_iter, rs)
        y_pred = best.predict(X_test)
        y_prob = best.predict_proba(X_test)[:, 1]
        rows.append({
            "Modelo": name,
            "CV_F1": round(cv_score, 4),
            "Accuracy": round(accuracy_score(y_te, y_pred), 4),
            "F1": round(f1_score(y_te, y_pred, zero_division=0), 4),
            "Precision": round(precision_score(y_te, y_pred, zero_division=0), 4),
            "Recall": round(recall_score(y_te, y_pred, zero_division=0), 4),
            "ROC_AUC": round(roc_auc_score(y_te, y_prob), 4),
        })
        joblib.dump(best, MODELS_DIR / f"{ds_name}_{name.lower()}_clf_tuned.joblib")
        logger.info("[%s] tuned clf %s — CV_F1=%.4f test_F1=%.4f",
                    ds_name, name, cv_score, rows[-1]["F1"])
    report = pd.DataFrame(rows).sort_values("F1", ascending=False).reset_index(drop=True)
    logger.info("[%s] tuned clf — mejor por F1: %s (%.4f)", ds_name,
                report.iloc[0]["Modelo"], report.iloc[0]["F1"])
    return report


def tune_regressors(X_train, y_train, X_test, y_test, params, ds_name):
    # Tunea los regresores con RandomizedSearchCV (scoring=neg-MAE, CV en train),
    # evalua el mejor de cada familia en test y guarda {ds}_{modelo}_reg_tuned.joblib.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    y_tr, y_te = y_train.squeeze(), y_test.squeeze()
    rs = params.get("random_state", 42)
    cv = params.get("cv_folds", 5)
    n_iter = params.get("rs_n_iter", 40)
    rows = []
    for name, (pipe, dist) in _reg_search_spaces(rs).items():
        best, cv_score = _search(
            pipe, dist, X_train, y_tr, "neg_mean_absolute_error", cv, n_iter, rs)
        y_pred = best.predict(X_test)
        rows.append({
            "Modelo": name,
            "CV_MAE": round(-cv_score, 4),
            "R2": round(r2_score(y_te, y_pred), 4),
            "MAE": round(mean_absolute_error(y_te, y_pred), 4),
            "RMSE": round(float(np.sqrt(mean_squared_error(y_te, y_pred))), 4),
        })
        joblib.dump(best, MODELS_DIR / f"{ds_name}_{name.lower()}_reg_tuned.joblib")
        logger.info("[%s] tuned reg %s — CV_MAE=%.4f test_MAE=%.4f",
                    ds_name, name, -cv_score, rows[-1]["MAE"])
    report = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
    logger.info("[%s] tuned reg — mejor por MAE: %s (%.4f)", ds_name,
                report.iloc[0]["Modelo"], report.iloc[0]["MAE"])
    return report
