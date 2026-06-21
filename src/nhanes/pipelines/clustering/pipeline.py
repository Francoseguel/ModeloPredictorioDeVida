from functools import partial

from kedro.pipeline import Pipeline, node

from .nodes import cluster_dataset

# Datasets sobre los que se descubren fenotipos:
#   master -> fenotipo de envejecimiento global (todos los bloques)
#   lab    -> fenotipo biomarcador
#   diet   -> patrones dieteticos (todo numerico, ideal para clustering)
CLUSTER_DATASETS = ["master", "lab", "diet"]


def create_pipeline(**kwargs) -> Pipeline:
    nodes = []
    for ds in CLUSTER_DATASETS:
        nodes.append(
            node(
                partial(cluster_dataset, ds_name=ds),
                inputs=[f"{ds}_clean", "params:modeling"],
                outputs=[f"{ds}_cluster_report", f"{ds}_cluster_labels"],
                name=f"cluster_{ds}",
            )
        )
    return Pipeline(nodes)
