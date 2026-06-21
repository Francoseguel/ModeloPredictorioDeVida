import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import KNNImputer
from sklearn.metrics import (
    calinski_harabasz_score, davies_bouldin_score, silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

logger = logging.getLogger(__name__)
MODELS_DIR = Path(__file__).parents[4] / "models" / "trained_models"


# =============================================================================
# CLUSTERING NO SUPERVISADO — fenotipos de envejecimiento
# -----------------------------------------------------------------------------
# No hay split train/test (no supervisado): se ajusta sobre el dataset completo.
# Preprocesado especifico de clustering (decision revisada con el skill):
#   - RobustScaler (mediana + IQR) en vez de StandardScaler: los biomarcadores
#     NHANES son muy asimetricos con outliers, y KMeans/DBSCAN son distancia-puras
#     -> StandardScaler dejaria que unos pocos extremos dominen los clusters.
#   - KNNImputer sobre lo ya escalado (mismo orden que el resto del proyecto).
#   - PCA para reducir ruido/colinealidad antes de medir distancias; DBSCAN usa
#     una reduccion mas agresiva (dbscan_pca_components) por su sensibilidad a la
#     dimensionalidad.
# Solo se usan features NUMERICAS (las one-hot 0/1 distorsionan la distancia
# frente a las continuas estandarizadas — problema de escalas mixtas).
# Metricas (skill): Silhouette y Calinski-Harabasz (mas alto mejor), Davies-Bouldin
# (mas bajo mejor). Se elige k de KMeans por mejor Silhouette.
# =============================================================================


def cluster_dataset(df_clean: pd.DataFrame, params: dict, ds_name: str) -> tuple:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    rs = params.get("random_state", 42)
    n_init = (params.get("cluster_kmeans") or {}).get("n_init", 10)
    k_max = params.get("kmeans_k_max", 8)
    knn_k = params.get("knn_neighbors", 5)

    num = df_clean.select_dtypes(include="number")
    logger.info("[%s] clustering: %d features numericas, %d filas",
                ds_name, num.shape[1], num.shape[0])

    # Preprocesado: RobustScaler -> KNNImpute (si quedan NaN)
    Xs = RobustScaler().fit_transform(num)
    if np.isnan(Xs).any():
        Xs = KNNImputer(n_neighbors=knn_k).fit_transform(Xs)

    # PCA principal (para KMeans / Agglomerative / GMM)
    pca_n = min(params.get("pca_n_components", 15), Xs.shape[1])
    pca = PCA(n_components=pca_n, random_state=rs)
    Xr = pca.fit_transform(Xs)
    logger.info("[%s] PCA %d comp -> %.1f%% varianza explicada",
                ds_name, pca_n, pca.explained_variance_ratio_.sum() * 100)

    rows = []

    # --- KMeans: barrido de k, mejor por Silhouette ---
    best = {"k": None, "sil": -1.0}
    for k in range(2, k_max + 1):
        km = KMeans(n_clusters=k, n_init=n_init, random_state=rs).fit(Xr)
        labels = km.labels_
        sil = silhouette_score(Xr, labels)
        rows.append({
            "Metodo": "KMeans", "Config": f"k={k}", "N_Clusters": k,
            "Silhouette": round(sil, 4),
            "Calinski_Harabasz": round(calinski_harabasz_score(Xr, labels), 1),
            "Davies_Bouldin": round(davies_bouldin_score(Xr, labels), 4),
            "Ruido_pct": 0.0, "Inertia": round(km.inertia_, 1),
        })
        if sil > best["sil"]:
            best = {"k": k, "sil": sil}

    # --- DBSCAN: grid de (eps, min_samples) sobre PCA mas agresivo ---
    dpca_n = min(params.get("dbscan_pca_components", 5), Xs.shape[1])
    Xd = PCA(n_components=dpca_n, random_state=rs).fit_transform(Xs)
    for g in (params.get("cluster_dbscan_grid") or []):
        eps, ms = g["eps"], g["min_samples"]
        labels = DBSCAN(eps=eps, min_samples=ms).fit_predict(Xd)
        n_clu = len(set(labels)) - (1 if -1 in labels else 0)
        noise = float((labels == -1).mean() * 100)
        if n_clu >= 2:
            m = labels != -1
            sil = round(silhouette_score(Xd[m], labels[m]), 4)
            cal = round(calinski_harabasz_score(Xd[m], labels[m]), 1)
            dav = round(davies_bouldin_score(Xd[m], labels[m]), 4)
        else:
            sil = cal = dav = None
        rows.append({
            "Metodo": "DBSCAN", "Config": f"eps={eps},min={ms}", "N_Clusters": n_clu,
            "Silhouette": sil, "Calinski_Harabasz": cal, "Davies_Bouldin": dav,
            "Ruido_pct": round(noise, 1), "Inertia": None,
        })

    # --- Comparacion de algoritmos al mejor k (Agglomerative, GMM) ---
    comparativos = {
        "Agglomerative": AgglomerativeClustering(n_clusters=best["k"], linkage="ward"),
        "GaussianMixture": GaussianMixture(n_components=best["k"], random_state=rs),
    }
    for name, algo in comparativos.items():
        labels = algo.fit_predict(Xr)
        rows.append({
            "Metodo": name, "Config": f"k={best['k']}", "N_Clusters": best["k"],
            "Silhouette": round(silhouette_score(Xr, labels), 4),
            "Calinski_Harabasz": round(calinski_harabasz_score(Xr, labels), 1),
            "Davies_Bouldin": round(davies_bouldin_score(Xr, labels), 4),
            "Ruido_pct": 0.0, "Inertia": None,
        })

    report = pd.DataFrame(rows)

    # --- Modelo final reutilizable (mejor KMeans) como Pipeline completo ---
    pipe = Pipeline([
        ("scaler", RobustScaler()),
        ("imputer", KNNImputer(n_neighbors=knn_k)),
        ("pca", PCA(n_components=pca_n, random_state=rs)),
        ("kmeans", KMeans(n_clusters=best["k"], n_init=n_init, random_state=rs)),
    ]).fit(num)
    joblib.dump(pipe, MODELS_DIR / f"{ds_name}_kmeans_cluster.joblib")

    labels_df = pd.DataFrame(
        {"cluster": pipe.named_steps["kmeans"].labels_}, index=num.index)

    logger.info("[%s] mejor KMeans k=%d (Silhouette=%.4f); etiquetas %s",
                ds_name, best["k"], best["sil"], labels_df.shape)
    return report, labels_df
