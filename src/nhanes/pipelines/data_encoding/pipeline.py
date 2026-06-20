from kedro.pipeline import Pipeline, node

from .nodes import encode_dataset

# Solo demo y diet (sin target). exam/lab/quest se encodean POST-split en
# data_transformation (fit en train) para evitar data leakage.
DATASETS = ["demo", "diet"]


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                encode_dataset,
                inputs=[f"{ds}_imputed", f"params:{ds}"],
                outputs=f"{ds}_encoded",
                name=f"encode_{ds}",
            )
            for ds in DATASETS
        ]
    )
