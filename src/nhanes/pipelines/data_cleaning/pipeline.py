from kedro.pipeline import Pipeline, node

from .nodes import clean_dataset

# Datasets que pasan por la limpieza. demo y diet van sin target (covariables/features).
DATASETS = ["exam", "lab", "quest", "demo", "diet"]


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                clean_dataset,
                inputs=[f"{ds}_intermediate", f"params:{ds}"],
                outputs=[f"{ds}_clean", f"{ds}_target_raw"],
                name=f"clean_{ds}",
            )
            for ds in DATASETS
        ]
    )
