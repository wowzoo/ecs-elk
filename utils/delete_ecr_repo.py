import os
import boto3


if __name__ == "__main__":
    repo_name = os.environ["REPO_NAME"]
    ecr_client = boto3.client("ecr")

    response = ecr_client.describe_images(
        repositoryName=repo_name
    )

    image_ids = []
    for res in response["imageDetails"]:
        for image_tag in res["imageTags"]:
            image_ids.append(
                {
                    "imageDigest": res["imageDigest"],
                    "imageTag": image_tag
                }
            )

    print(image_ids)
    if len(image_ids) > 0:
        ecr_client.batch_delete_image(
            repositoryName=repo_name,
            imageIds=image_ids
        )

    ecr_client.delete_repository(
        repositoryName=repo_name
    )
