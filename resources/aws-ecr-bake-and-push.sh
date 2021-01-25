#!/usr/bin/env zsh

ECR_URL="${CDK_ACCOUNT}.dkr.ecr.${CDK_REGION}.amazonaws.com"

docker build -t "${REPO_NAME}" .
docker tag "${REPO_NAME}:latest" "${ECR_URL}/${REPO_NAME}:latest"
docker push "${ECR_URL}/${REPO_NAME}:latest"
