from kedro.pipeline import Pipeline, node

from .nodes import transform_train_test

# Transformacion post-split (fit en train) para los datasets supervisados.
SUPERVISED = ["exam", "lab", "quest"]


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                transform_train_test,
                inputs=[f"{ds}_X_train_raw", f"{ds}_X_test_raw", f"params:{ds}"],
                outputs=[f"{ds}_X_train", f"{ds}_X_test"],
                name=f"transform_{ds}",
            )
            for ds in SUPERVISED
        ]
    )
