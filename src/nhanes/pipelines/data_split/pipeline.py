from kedro.pipeline import Pipeline, node

from .nodes import create_target, split_dataset

# Datasets con target supervisado. demo/diet no tienen target (solo clustering).
SUPERVISED = ["exam", "lab", "quest"]


def create_pipeline(**kwargs) -> Pipeline:
    nodes = []
    for ds in SUPERVISED:
        # lab calcula PhenoAge -> necesita la edad cronologica de demo.
        ct_inputs = [f"{ds}_target_raw", f"params:{ds}"]
        if ds == "lab":
            ct_inputs.append("demo_intermediate")
        nodes.append(
            node(
                create_target,
                inputs=ct_inputs,
                outputs=f"{ds}_target",
                name=f"target_{ds}",
            )
        )
        # Se parte del CLEAN crudo (con NaN, sin escalar/encodear): el escalado,
        # la imputacion y el encoding se hacen DESPUES del split (data_transformation)
        # ajustados solo con train, para evitar data leakage.
        nodes.append(
            node(
                split_dataset,
                inputs=[f"{ds}_clean", f"{ds}_target", "params:modeling"],
                outputs=[
                    f"{ds}_X_train_raw", f"{ds}_X_test_raw",
                    f"{ds}_y_train_clf", f"{ds}_y_test_clf",
                    f"{ds}_y_train_reg", f"{ds}_y_test_reg",
                ],
                name=f"split_{ds}",
            )
        )
    return Pipeline(nodes)
