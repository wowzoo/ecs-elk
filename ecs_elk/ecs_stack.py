from aws_cdk import (
    core,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
)


class ECSStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 vpc_id: str, security_group_id: str,
                 region: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id
        )
        sg = ec2.SecurityGroup.from_lookup(
            self,
            "SecurityGroup",
            security_group_id=security_group_id
        )

        cluster = ecs.Cluster(
            self,
            "KeehyunECSCluster",
            cluster_name="KeehyunECSCluster",
            vpc=vpc
        )

        execution_role = iam.Role(
            self,
            "ECSTaskExecutionRole",
            role_name="ECSTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=["*"]
            )
        )

        task_role = iam.Role(
            self,
            "ECSInstanceRole",
            role_name="ECSInstanceRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeTags",
                    "ecs:CreateCluster",
                    "ecs:DeregisterContainerInstance",
                    "ecs:DiscoverPollEndpoint",
                    "ecs:Poll",
                    "ecs:RegisterContainerInstance",
                    "ecs:StartTelemetrySession",
                    "ecs:UpdateContainerInstancesState",
                    "ecs:Submit*",
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                    "es:ESHttp*"
                ],
                resources=["*"]
            )
        )

        nginx_task_def = ecs.FargateTaskDefinition(
            self,
            "NginxFirelensTest",
            cpu=512,
            memory_limit_mib=1024,
            execution_role=execution_role,
            family="nginx-firelens-test",
            task_role=task_role,
        )

        vpc_es_domain_endpoint = ssm.StringParameter.from_string_parameter_attributes(
            self,
            "VPCESDomainEndpoint",
            parameter_name="vpc-es-domain-endpoint"
        ).string_value

        nginx_container = nginx_task_def.add_container(
            "nginx-test",
            image=ecs.ContainerImage.from_registry("nginx"),
            essential=True,
            logging=ecs.LogDrivers.firelens(
                options={
                    "Name": "cloudwatch",
                    "region": region,
                    "log_group_name": f"/aws/ecs/containerinsights/{cluster.cluster_name}/application",
                    "auto_create_group": "true",
                    "log_stream_name": "nginx-test"
                }
                # options={
                #     "Name": "es",
                #     "Host": vpc_es_domain_endpoint,
                #     "Port": "443",
                #     "Index": "nginx_index",
                #     "Type": "nginx_type",
                #     "Aws_Auth": "On",
                #     "Aws_Region": region,
                #     "tls": "On"
                # }
            ),
            memory_reservation_mib=100,
        )

        nginx_container.add_port_mappings(
            ecs.PortMapping(container_port=80)
        )

        nginx_task_def.add_firelens_log_router(
            "log_router",
            image=ecs.ContainerImage.from_registry("amazon/aws-for-fluent-bit:latest"),
            firelens_config=ecs.FirelensConfig(
                type=ecs.FirelensLogRouterType.FLUENTBIT
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="firelens",
            )
        )

        service = ecs.FargateService(
            self,
            "KeehyunECSService",
            service_name="KeehyunECSService",
            cluster=cluster,
            task_definition=nginx_task_def,
            desired_count=1,
            enable_ecs_managed_tags=True,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_groups=[sg],
        )
