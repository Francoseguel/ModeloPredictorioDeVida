from functools import partial

from kedro.pipeline import Pipeline, node

from .nodes import train_classifiers, train_regressors

# Mismos datasets supervisados que data_split.
SUPERVISED = ["exam", "lab", "quest"]


def create_pipeline(**kwargs) -> Pipeline:
    nodes = []
    for ds in SUPERVISED:
        nodes.append(
            node(
                partial(train_classifiers, ds_name=ds),
                inputs=[
                    f"{ds}_X_train", f"{ds}_y_train_clf",
                    f"{ds}_X_test", f"{ds}_y_test_clf",
                    "params:modeling",
                ],
                outputs=f"{ds}_clf_report",
                name=f"clf_{ds}",
            )
        )
        nodes.append(
            node(
                partial(train_regressors, ds_name=ds),
                inputs=[
                    f"{ds}_X_train", f"{ds}_y_train_reg",
                    f"{ds}_X_test", f"{ds}_y_test_reg",
                    "params:modeling",
                ],
                outputs=f"{ds}_reg_report",
                name=f"reg_{ds}",
            )
        )
    return Pipeline(nodes)
