from kedro.pipeline import Pipeline, node

from .nodes import merge_master


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                merge_master,
                inputs=[
                    "exam_clean", "lab_clean", "quest_clean",
                    "diet_clean", "demo_clean", "lab_target_raw",
                ],
                outputs=["master_clean", "master_target_raw"],
                name="merge_master",
            )
        ]
    )
