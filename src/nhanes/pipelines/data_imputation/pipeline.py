from kedro.pipeline import Pipeline, node

from .nodes import impute_dataset

# Solo demo y diet (sin target): se imputan sobre todo el dataset porque no tienen
# split supervisado. exam/lab/quest se imputan POST-split en data_transformation
# (fit en train) para evitar data leakage.
DATASETS = ["demo", "diet"]


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                impute_dataset,
                inputs=[f"{ds}_clean", f"params:{ds}"],
                outputs=f"{ds}_imputed",
                name=f"impute_{ds}",
            )
            for ds in DATASETS
        ]
    )
