import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error,
    mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score,
)
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
