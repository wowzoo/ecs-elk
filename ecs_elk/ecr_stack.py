from aws_cdk import (
    core,
    aws_ecr as ecr,
)


class ECRStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 repo_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repository = ecr.Repository(
            self,
            "ECSInELKRepo",
            repository_name=repo_name,
            image_scan_on_push=True,
        )
