from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_elasticsearch as es,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_route53 as route53,
    aws_route53_targets as alias,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets
)


class ElasticSearchVPCStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 account: str, region: str, es_domain_name: str,
                 vpc_id: str, security_group_id: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        user_pool_id = ssm.StringParameter.from_string_parameter_attributes(
            self, "UserPoolIDStringParameter", parameter_name="user-pool-id"
        ).string_value

        identity_pool_id = ssm.StringParameter.from_string_parameter_attributes(
            self, "IdentityPoolIDStringParameter", parameter_name="identity-pool-id"
        ).string_value

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

        es_admin_role_arn = f"arn:aws:iam::{account}:role/KeehyunCognitoESAdminRole"

        cognito_es_role = iam.Role(
            self,
            "KeehyunCognitoVPCESRole",
            role_name="KeehyunCognitoVPCESRole",
            assumed_by=iam.ServicePrincipal("es.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonESCognitoAccess"),
            ]
        )

        es_domain = es.Domain(
            self,
            "KeehyunVPCES",
            domain_name=es_domain_name,
            version=es.ElasticsearchVersion.V7_7,
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest=es.EncryptionAtRestOptions(enabled=True),
            fine_grained_access_control=es.AdvancedSecurityOptions(
                master_user_arn=es_admin_role_arn
            ),
            cognito_kibana_auth=es.CognitoOptions(
                user_pool_id=user_pool_id,
                identity_pool_id=identity_pool_id,
                role=cognito_es_role
            ),
            vpc_options=es.VpcOptions(
                security_groups=[sg],
                subnets=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnets
            ),
            zone_awareness=es.ZoneAwarenessConfig(
                availability_zone_count=2,
                enabled=True
            ),
            capacity=es.CapacityConfig(
                master_node_instance_type="r5.large.elasticsearch",
                master_nodes=3,
                data_node_instance_type="r5.large.elasticsearch",
                data_nodes=4
            ),
            logging=es.LoggingOptions(
                app_log_enabled=True,
                audit_log_enabled=True,
                slow_index_log_enabled=True,
                slow_search_log_enabled=True
            ),
            access_policies=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "es:*"
                    ],
                    principals=[iam.ArnPrincipal(es_admin_role_arn)],
                    resources=[f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/*"]
                )
            ],
        )

        ssm.StringParameter(
            self,
            "VPCESDomainEndpointStringParameter",
            parameter_name="vpc-es-domain-endpoint",
            string_value=es_domain.domain_endpoint
        )

        core.CfnOutput(
            self,
            "Output",
            value=es_domain.domain_endpoint
        )

        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            cpu_type=ec2.AmazonLinuxCpuType.X86_64,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE,
            virtualization=ec2.AmazonLinuxVirt.HVM,
        )

        kibana_proxy = ec2.Instance(
            self,
            "KibanaProxyInstance",
            instance_name="kibana-proxy",
            instance_type=ec2.InstanceType("t3.medium"),
            machine_image=amzn_linux,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_group=sg,
            key_name="eksworkshop",
        )
