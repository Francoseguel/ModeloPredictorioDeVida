from kedro.pipeline import Pipeline, node

from .nodes import build_cohort, clean_dataset

# Datasets que pasan por la limpieza. demo y diet van sin target (covariables/features).
DATASETS = ["exam", "lab", "quest", "demo", "diet"]


def create_pipeline(**kwargs) -> Pipeline:
    nodes = [
        node(
            build_cohort,
            inputs=["demo_intermediate", "params:cohort"],
            outputs="cohort_index",
            name="build_cohort",
        )
    ]
    nodes += [
        node(
            clean_dataset,
            inputs=[f"{ds}_intermediate", f"params:{ds}", "cohort_index"],
            outputs=[f"{ds}_clean", f"{ds}_target_raw"],
            name=f"clean_{ds}",
        )
        for ds in DATASETS
    ]
    return Pipeline(nodes)
