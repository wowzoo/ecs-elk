from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_cognito as cg,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ssm as ssm,
)


class CognitoStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 region: str, account: str, es_domain_name: str,
                 vpc_id: str, security_group_id: str,
                 **kwargs) -> None:
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

        # lambda_role = iam.Role(
        #     self,
        #     "OctankBaseCognito_PostConfirmationLambdaRole",
        #     role_name="OctankBaseCognito_PostConfirmationLambdaRole",
        #     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        #     managed_policies=[
        #         iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambdaFullAccess"),
        #         iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess"),
        #         iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2FullAccess"),
        #     ]
        # )

        # self._lambda_code = lambda_.Code.from_cfn_parameters()

        # Post Confirmation Lambda
        # post_confirmation_lambda = lambda_.Function(
        #     self,
        #     "OctankCognitoPostConfirmation",
        #     function_name="OctankCognitoPostConfirmation",
        #     handler="lambda_handler.handler",
        #     runtime=lambda_.Runtime.PYTHON_3_8,
        #     code=self._lambda_code,
        #     timeout=core.Duration.seconds(7),
        #     role=lambda_role,
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PRIVATE
        #     ),
        #     security_groups=[sg]
        # )

        self._user_pool = cg.UserPool(
            self,
            "KeehyunUserPool",
            user_pool_name="KeehyunUserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cg.SignInAliases(
                email=True
            ),
            user_verification=cg.UserVerificationConfig(
                email_subject="Verify your email",
                email_body="Hello, Thanks for signing up! Your verification code is {####}",
                email_style=cg.VerificationEmailStyle.CODE,
            ),
            auto_verify=cg.AutoVerifiedAttrs(email=True),
            standard_attributes=cg.StandardAttributes(
                email=cg.StandardAttribute(
                    required=True,
                    mutable=False
                ),
            ),
            password_policy=cg.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_digits=True,
                temp_password_validity=core.Duration.days(3)
            ),
            account_recovery=cg.AccountRecovery.EMAIL_ONLY,
            # lambda_triggers=cg.UserPoolTriggers(
            #     post_confirmation=post_confirmation_lambda
            # )
        )

        client = self._user_pool.add_client(
            "KeehyunUserPoolAppClient",
            user_pool_client_name="KeehyunUserPoolAppClient",
            generate_secret=False
        )

        self._user_pool.add_domain(
            "KeehyunCognitoDomain",
            cognito_domain=cg.CognitoDomainOptions(domain_prefix="keehyun")
        )

        core.CfnOutput(
            self,
            "UserPoolID",
            value=self._user_pool.user_pool_id
        )

        core.CfnOutput(
            self,
            "AppClientID",
            value=client.user_pool_client_id
        )

        # Identity Pool
        self._identity_pool = cg.CfnIdentityPool(
            self,
            "KeehyunIdentityPool",
            identity_pool_name="KeehyunIdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cg.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=client.user_pool_client_id,
                    provider_name=self._user_pool.user_pool_provider_name
                )
            ]
        )

        unauthenticated_role = iam.Role(
            self,
            "KeehyunCognitoDefaultUnauthenticatedRole",
            role_name="KeehyunCognitoDefaultUnauthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                federated='cognito-identity.amazonaws.com',
                conditions={
                    "StringEquals": {
                       "cognito-identity.amazonaws.com:aud": self._identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                       "cognito-identity.amazonaws.com:amr": "unauthenticated",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            )
        )

        unauthenticated_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "mobileanalytics:PutEvents",
                    "cognito-sync:*",
                ],
                resources=["*"]
            )
        )

        authenticated_role = iam.Role(
            self,
            "KeehyunCognitoDefaultAuthenticatedRole",
            role_name="KeehyunCognitoDefaultAuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                federated='cognito-identity.amazonaws.com',
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self._identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            )
        )

        authenticated_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "mobileanalytics:PutEvents",
                    "cognito-sync:*",
                    "cognito-identity:*"
                ],
                resources=["*"]
            )
        )

        cg.CfnIdentityPoolRoleAttachment(
            self,
            "DefaultValid",
            identity_pool_id=self._identity_pool.ref,
            roles={
                'unauthenticated': unauthenticated_role.role_arn,
                'authenticated': authenticated_role.role_arn
            }
        )

        # ElasticSearch Admin Group
        es_admin_role = iam.Role(
            self,
            "KeehyunCognitoESAdminRole",
            role_name="KeehyunCognitoESAdminRole",
            assumed_by=iam.FederatedPrincipal(
                federated='cognito-identity.amazonaws.com',
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self._identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            )
        )

        es_admin_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:es:{region}:{account}:domain/{es_domain_name}/*"],
                actions=["es:ESHttp*"]
            )
        )

        cg.CfnUserPoolGroup(
            self,
            "KeehyunUserPoolGroup",
            user_pool_id=self._user_pool.user_pool_id,
            group_name="ESAdmin",
            description="ElasticSearch Admin User",
            role_arn=es_admin_role.role_arn,
            precedence=0
        )

        ssm.StringParameter(
            self,
            "UserPoolIDStringParameter",
            parameter_name="user-pool-id",
            string_value=self._user_pool.user_pool_id
        )

        ssm.StringParameter(
            self,
            "UserPoolARNStringParameter",
            parameter_name="user-pool-arn",
            string_value=self._user_pool.user_pool_arn
        )

        ssm.StringParameter(
            self,
            "IdentityPoolIDStringParameter",
            parameter_name="identity-pool-id",
            string_value=self._identity_pool.ref
        )

    # @property
    # def lambda_code(self):
    #     return self._lambda_code
