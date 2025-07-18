from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput,
    Duration,
    aws_bedrock,
    Fn,
    CustomResource,
    custom_resources as cr
)
from constructs import Construct

class PortfolioArchitectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket name from FinancialAnalysisStack
        s3_bucket_name = "agenticai-6yhkxx7c"

        # Create Lambda execution role with basic permissions
        lambda_role = iam.Role(
            self, "PortfolioArchitectRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add inline policy for S3 GetObject
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="s3getobject",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject"
                ],
                resources=[
                    f"arn:aws:s3:::{s3_bucket_name}/*"
                ]
            )
        )

        # Create Lambda function
        self.portfolio_architect_function = _lambda.Function(
            self, "PortfolioArchitectFunction",
            function_name="lambda-portfolio-architect",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.X86_64,
            code=_lambda.Code.from_asset("files/lambda_portfolio_architect"),
            handler="lambda_function.lambda_handler",
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            layers=[
                _lambda.LayerVersion.from_layer_version_arn(
                    self, "YFinanceLayer",
                    "arn:aws:lambda:us-east-1:008211515677:layer:yfinance-layer:2"
                )
            ],
            environment={
                "S3_BUCKET_NAME": s3_bucket_name
            }
        )

        # Create Bedrock Agent role
        agent_role = iam.Role(
            self, "PortfolioArchitectAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Portfolio Architect Bedrock Agent"
        )

        # Add required permissions for the agent role
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[self.portfolio_architect_function.function_arn]
            )
        )

        # Create Bedrock Agent
        self.portfolio_architect_agent = aws_bedrock.CfnAgent(
            self, "PortfolioArchitectAgent",
            agent_name="portfolio_architect",
            agent_resource_role_arn=agent_role.role_arn,
            description="Portfolio architect agent for investment portfolio design",
            instruction="You are a professional investment designer. You must propose a specific investment portfolio based on the client's financial analysis results.\n\nInput Data:\nFinancial analysis results are provided in the following JSON format:\n{\n  \"risk_profile\": <risk propensity>,\n  \"risk_profile_reason\": <risk propensity assessment basis>,\n  \"required_annual_return_rate\": <required annual return rate>,\n  \"return_rate_reason\": <required return rate calculation basis and explanation>\n}\n\nYour Tasks:\n1. Carefully review and interpret the financial analysis results.\n2. Call the \"get_available_products\" action to get a list of available investment products. Each product is provided in \"ticker: description\" format.\n3. Select the 3 most suitable products from the obtained product list considering diversification and the client's financial analysis results.\n4. Call the \"get_product_data\" action simultaneously for each selected investment product to get recent price data.\n5. Analyze the obtained price data to determine final portfolio ratios. Consider the client's financial analysis results in a balanced way.\n6. Explain the portfolio composition rationale in detail.\n\nPlease respond in the following JSON format:\n{\n  \"portfolio_allocation\": {investment product allocation ratios} (e.g., {\"ticker1\": 50, \"ticker2\": 30, \"ticker3\": 20}),\n  \"strategy\": \"investment strategy explanation\",\n  \"reason\": \"portfolio composition rationale\"\n}\n\nConsider the following when responding:\n- Logically explain how the proposed portfolio will help achieve the client's investment goals.\n- Asset allocation ratios must be expressed as integers and total 100%.\n- When writing the portfolio composition rationale, always provide both ticker and description like \"QQQ(US Technology Stocks)\".",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0"
        )

        # Construct agent ARN
        agent_arn = Fn.sub(
            "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent/${AgentId}",
            {"AgentId": self.portfolio_architect_agent.attr_agent_id}
        )

        # Add Lambda permission for Bedrock Agent
        self.portfolio_architect_function.add_permission(
            "allow-bedrock-agent",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            source_arn=agent_arn,
            action="lambda:InvokeFunction"
        )

        # Create a Lambda function to update the agent
        update_agent_function = _lambda.Function(
            self, "UpdateAgentFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_inline("""
import boto3
import cfnresponse

def handler(event, context):
    try:
        if event['RequestType'] in ['Create', 'Update']:
            bedrock = boto3.client('bedrock-agent')
            
            # Get the agent ID from the physical resource ID or event
            agent_id = event.get('PhysicalResourceId') or event['ResourceProperties']['AgentId']
            
            # Update the agent with action groups
            bedrock.update_agent(
                agentId=agent_id,
                agentName='portfolio_architect',
                agentResourceRoleArn=event['ResourceProperties']['AgentRoleArn'],
                agentConfiguration={
                    'actionGroups': [{
                        'name': 'action-group-portfolio-architect',
                        'description': 'Action group for portfolio architect functions',
                        'actionGroupExecutor': {
                            'lambda': {
                                'functionArn': event['ResourceProperties']['LambdaArn'],
                                'functionVersion': 'LATEST'
                            }
                        },
                        'actions': [
                            {
                                'name': 'get_product_data',
                                'description': 'Gets recent price data for the selected investment product.',
                                'requiresConfirmation': False,
                                'inputParameters': [
                                    {
                                        'name': 'ticker',
                                        'description': 'Ticker of the investment product to look up',
                                        'type': 'STRING',
                                        'required': True
                                    }
                                ]
                            },
                            {
                                'name': 'get_available_products',
                                'description': 'Gets list of available investment products.',
                                'requiresConfirmation': False
                            }
                        ]
                    }]
                }
            )
            
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, agent_id)
        else:
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
"""),
            role=iam.Role(
                self, "UpdateAgentRole",
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ],
                inline_policies={
                    "BedrockAccess": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                effect=iam.Effect.ALLOW,
                                actions=["bedrock:UpdateAgent"],
                                resources=[agent_arn]
                            )
                        ]
                    )
                }
            )
        )

        # Create a custom resource provider
        provider = cr.Provider(
            self, "UpdateAgentProvider",
            on_event_handler=update_agent_function
        )

        # Create a custom resource to update the agent with action groups
        update_agent = CustomResource(
            self, "UpdateAgentActionGroups",
            service_token=provider.service_token,
            properties={
                "AgentId": self.portfolio_architect_agent.attr_agent_id,
                "AgentRoleArn": agent_role.role_arn,
                "LambdaArn": self.portfolio_architect_function.function_arn
            }
        )

        # Make sure the custom resource depends on the agent
        update_agent.node.add_dependency(self.portfolio_architect_agent)

        # Create a custom resource to create and prepare the agent alias
        prepare_alias = CustomResource(
            self, "PrepareAgentAlias",
            service_token=cr.Provider(
                self, "PrepareAliasProvider",
                on_event_handler=_lambda.Function(
                    self, "PrepareAliasFunction",
                    runtime=_lambda.Runtime.PYTHON_3_12,
                    handler="index.handler",
                    code=_lambda.Code.from_inline("""
import boto3
import cfnresponse

def handler(event, context):
    try:
        if event['RequestType'] in ['Create', 'Update']:
            bedrock = boto3.client('bedrock-agent')
            agent_id = event['ResourceProperties']['AgentId']
            
            # Create a new version from DRAFT
            version_response = bedrock.create_agent_version(
                agentId=agent_id,
                agentVersion='1.0'
            )
            
            # Create the alias pointing to the new version with on-demand throughput
            alias_response = bedrock.create_agent_alias(
                agentId=agent_id,
                agentAliasName='prod',
                routingConfiguration={
                    'routingStrategy': 'ON_DEMAND'
                }
            )
            
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'AliasArn': alias_response['agentAliasArn']
            })
        else:
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
"""),
                    role=iam.Role(
                        self, "PrepareAliasRole",
                        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                        ],
                        inline_policies={
                            "BedrockAccess": iam.PolicyDocument(
                                statements=[
                                    iam.PolicyStatement(
                                        effect=iam.Effect.ALLOW,
                                        actions=[
                                            "bedrock:CreateAgentVersion",
                                            "bedrock:CreateAgentAlias"
                                        ],
                                        resources=[agent_arn]
                                    )
                                ]
                            )
                        }
                    )
                )
            ),
            properties={
                "AgentId": self.portfolio_architect_agent.attr_agent_id
            }
        )

        # Make sure the alias preparation happens after the agent update
        prepare_alias.node.add_dependency(update_agent)

        # Output the Lambda function ARN
        CfnOutput(
            self, "PortfolioArchitectFunctionArn",
            value=self.portfolio_architect_function.function_arn,
            description="ARN of the Portfolio Architect Lambda function"
        )

        # Output the Lambda function name
        CfnOutput(
            self, "PortfolioArchitectFunctionName",
            value=self.portfolio_architect_function.function_name,
            description="Name of the Portfolio Architect Lambda function"
        )

        # Output the Bedrock Agent ID
        CfnOutput(
            self, "PortfolioArchitectAgentId",
            value=self.portfolio_architect_agent.attr_agent_id,
            description="ID of the Portfolio Architect Bedrock Agent"
        )

        # Output the Bedrock Agent ARN
        CfnOutput(
            self, "PortfolioArchitectAgentArn",
            value=agent_arn,
            description="ARN of the Portfolio Architect Bedrock Agent"
        )
