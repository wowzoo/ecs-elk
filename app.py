#!/usr/bin/env python3

import os
from aws_cdk import core
from ecs_elk.ecr_stack import ECRStack
from ecs_elk.auth_stack import CognitoStack
from ecs_elk.search_stack import ElasticSearchVPCStack
from ecs_elk.ecs_stack import ECSStack
from ecs_elk.firehose_stack import KinesisFirehoseStack

account = os.environ["CDK_ACCOUNT"]
region = os.environ["CDK_REGION"]
es_domain_name = os.environ["ES_DOMAIN_NAME"]
es_index_name = os.environ["ES_INDEX_NAME"]
es_type_name = os.environ["ES_TYPE_NAME"]
vpc_id = os.environ["VPC_ID"]
security_group_id = os.environ["SECURITY_GROUP_ID"]
repo_name = os.environ["REPO_NAME"]

app = core.App()

ECRStack(
    app,
    "ECRStack",
    repo_name=repo_name,
    env={"account": account, "region": region}
)

CognitoStack(
    app,
    "AuthCognito",
    region=region,
    account=account,
    es_domain_name=es_domain_name,
    vpc_id=vpc_id,
    security_group_id=security_group_id,
    env={"account": account, "region": region}
)

ElasticSearchVPCStack(
    app,
    "SearchVPCES",
    account=account,
    region=region,
    es_domain_name=es_domain_name,
    vpc_id=vpc_id,
    security_group_id=security_group_id,
    env={"account": account, "region": region}
)

KinesisFirehoseStack(
    app,
    "KinesisFirehoseStack",
    region=region,
    account=account,
    es_domain_name=es_domain_name,
    es_index_name=es_index_name,
    es_type_name=es_type_name,
    vpc_id=vpc_id,
    security_group_id=security_group_id,
    env={"account": account, "region": region}
)

ECSStack(
    app,
    "ECSStack",
    region=region,
    vpc_id=vpc_id,
    security_group_id=security_group_id,
    env={"account": account, "region": region}
)

core.Tags.of(app).add("Owner", "keehyun")

app.synth()
