import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_dynamodb as dynamodb,
    aws_secretsmanager as secretsmanager
)
from constructs import Construct

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "BookingChatbotVPC",
            max_azs=1, 
            subnet_configuration=[
                ec2.SubnetConfiguration(                   
                    name="LambdaSubnet", 
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="DbSubnet", # Subnet cho RDS
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # === 2. TẠO DATABASE (POSTGRESQL) [Số 9] ===
        
        self.rds_sg = ec2.SecurityGroup(
            self, "RdsSecurityGroup",
            vpc=self.vpc,
            description="Security Group for RDS",
            allow_all_outbound=True
        )
        
        rds_credentials = rds.Credentials.from_generated_secret("RdsAdminUser")
        self.rds_secret = rds_credentials.secret 
        
        self.rds_instance = rds.DatabaseInstance(
            self, "PostgresDB",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_15),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="DbSubnet"),
            security_groups=[self.rds_sg],
            credentials=rds_credentials,
            database_name="chatbot_db",
            allocated_storage=20, 
            multi_az=False, 
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # === 3. TẠO DYNAMODB TABLE  ===
        self.cache_table = dynamodb.Table(
            self, "ChatbotCache",
            partition_key=dynamodb.Attribute(name="session_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

      # === 4. TẠO SECURITY GROUP CHO LAMBDA ===
        
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security Group for Lambdas",
            allow_all_outbound=True
        )
        
        # Mở cổng cho Lambda kết nối RDS
        self.rds_sg.add_ingress_rule(self.lambda_sg, ec2.Port.tcp(5432), "Allow Lambda to connect to RDS")

        # TẠO VPC ENDPOINTS``
        
        
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )
        
        
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=ec2.SubnetSelection(subnet_group_name="LambdaSubnet")
        )

        self.vpc.add_interface_endpoint(
            "BedrockRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            subnets=ec2.SubnetSelection(subnet_group_name="LambdaSubnet")
        )
        
        self.vpc.add_interface_endpoint(
            "AthenaEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ATHENA,
            subnets=ec2.SubnetSelection(subnet_group_name="LambdaSubnet")
        )
        

        # (Luồng #1 & #4) Cho gọi Lambda (ChatOrchestrator -> ScheduleExecutor, Admin -> RAG)
        self.vpc.add_interface_endpoint(
            "LambdaEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.LAMBDA,
            subnets=ec2.SubnetSelection(subnet_group_name="LambdaSubnet")
        )
        
        
        # === 6. XUẤT OUTPUTS ===
        cdk.CfnOutput(self, "VPCId", value=self.vpc.vpc_id)
        cdk.CfnOutput(self, "RDSAddress", value=self.rds_instance.db_instance_endpoint_address)
        cdk.CfnOutput(self, "RDSSecretArn", value=self.rds_secret.secret_arn)
        cdk.CfnOutput(self, "CacheTableName", value=self.cache_table.table_name)