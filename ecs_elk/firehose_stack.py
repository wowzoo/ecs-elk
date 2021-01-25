from aws_cdk import (
    core,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_kinesisfirehose as firehose,
    aws_logs as cloudwatch_logs,
)


class KinesisFirehoseStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 vpc_id: str, security_group_id: str,
                 region: str, account: str,
                 es_domain_name: str, es_index_name: str, es_type_name: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        delivery_stream_name = "keehyun-firehose"

        firehose_log_group = cloudwatch_logs.LogGroup(
            self,
            "KinesisFirehoseLogGroup",
            log_group_name=f"/aws/kinesisfirehose/{delivery_stream_name}",
            retention=cloudwatch_logs.RetentionDays.INFINITE
        )

        s3_log_stream = cloudwatch_logs.LogStream(
            self,
            "S3LogStream",
            log_group=firehose_log_group,
            log_stream_name="S3Delivery"
        )

        es_log_stream = cloudwatch_logs.LogStream(
            self,
            "ESLogStream",
            log_group=firehose_log_group,
            log_stream_name="ElasticsearchDelivery"
        )

        vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id
        )
        # sg = ec2.SecurityGroup.from_lookup(
        #     self,
        #     "SecurityGroup",
        #     security_group_id=security_group_id
        # )

        # S3 bucket
        backup_bucket = s3.Bucket(
            self,
            "FirehoseBackupBucket",
            bucket_name="firehose-log-storage",
        )

        # firehose delivery role
        firehose_delivery_role = iam.Role(
            self,
            "KinesisFirehoseDeliveryRole",
            role_name="KinesisFirehoseDeliveryRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )

        # VPC permission
        firehose_delivery_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeVpcs",
                    "ec2:DescribeVpcAttribute",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:CreateNetworkInterface",
                    "ec2:CreateNetworkInterfacePermission",
                    "ec2:DeleteNetworkInterface"
                ],
                resources=["*"]
            )
        )

        # S3 permission
        firehose_delivery_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:AbortMultipartUpload",
                    "s3:GetBucketLocation",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                    "s3:PutObject"
                ],
                resources=[
                    f"arn:aws:s3:::{backup_bucket.bucket_name}",
                    f"arn:aws:s3:::{backup_bucket.bucket_name}/*"
                ]
            )
        )

        # ES permission
        firehose_delivery_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "es:DescribeElasticsearchDomain",
                    "es:DescribeElasticsearchDomains",
                    "es:DescribeElasticsearchDomainConfig",
                    "es:ESHttpPost",
                    "es:ESHttpPut"
                ],
                resources=[
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/*",
                ]
            )
        )
        firehose_delivery_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "es:ESHttpGet"
                ],
                resources=[
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/_all/_settings",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/_cluster/stats",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/{es_index_name}*/_mapping/{es_index_name}",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/_nodes",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/_nodes/stats",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/_nodes/*/stats",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/_stats",
                    f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/{es_index_name}*/_stats"
                ]
            )
        )

        # Kinesis permission
        firehose_delivery_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kinesis:DescribeStream",
                    "kinesis:GetShardIterator",
                    "kinesis:GetRecords",
                    "kinesis:ListShards"
                ],
                resources=[
                    f"arn:aws:kinesis:{region}:{account}:stream/{delivery_stream_name}",
                ]
            )
        )

        # CloudWatch logging permission
        firehose_delivery_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:PutLogEvents"
                ],
                resources=[
                    f"arn:aws:logs:{region}:{account}:log-group/aws/kinesisfirehose/{delivery_stream_name}:log-stream:*",
                ]
            )
        )

        s3_logging_config = firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
            enabled=True,
            log_group_name=firehose_log_group.log_group_name,
            log_stream_name=s3_log_stream.log_stream_name
        )

        s3_config = firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
            bucket_arn=backup_bucket.bucket_arn,
            role_arn=firehose_delivery_role.role_arn,
            cloud_watch_logging_options=s3_logging_config
        )

        vpc_config = firehose.CfnDeliveryStream.VpcConfigurationProperty(
            role_arn=firehose_delivery_role.role_arn,
            security_group_ids=[security_group_id],
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnet_ids
        )

        es_logging_config = firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
            enabled=True,
            log_group_name=firehose_log_group.log_group_name,
            log_stream_name=es_log_stream.log_stream_name
        )

        # vpc_es_domain_endpoint = ssm.StringParameter.from_string_parameter_attributes(
        #     self,
        #     "VPCESDomainEndpoint",
        #     parameter_name="vpc-es-domain-endpoint"
        # ).string_value

        es_config = firehose.CfnDeliveryStream.ElasticsearchDestinationConfigurationProperty(
            index_name=es_index_name,
            # type_name=es_type_name,
            role_arn=firehose_delivery_role.role_arn,
            index_rotation_period="OneHour",
            s3_backup_mode="AllDocuments",
            s3_configuration=s3_config,
            # cluster_endpoint=f"https://{vpc_es_domain_endpoint}",
            domain_arn=f"arn:aws:es:{region}:{account}:domain/{es_domain_name}",
            vpc_configuration=vpc_config,
            cloud_watch_logging_options=es_logging_config
        )

        firehose_delivery_stream = firehose.CfnDeliveryStream(
            self,
            "KeehyunFirehose",
            delivery_stream_name=delivery_stream_name,
            delivery_stream_type="DirectPut",
            elasticsearch_destination_configuration=es_config,
            tags=[core.CfnTag(key="Owner", value="keehyun")],
        )

        firehose_delivery_stream.node.add_dependency(firehose_delivery_role)
