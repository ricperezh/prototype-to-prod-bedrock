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

class RiskManagerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, yfinance_layer: _lambda.ILayerVersion, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda execution role with basic permissions
        lambda_role = iam.Role(
            self, "RiskManagerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Create Lambda function
        self.risk_manager_function = _lambda.Function(
            self, "RiskManagerFunction",
            function_name="lambda-risk-manager",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.X86_64,
            code=_lambda.Code.from_asset("files/lambda_risk_manager"),
            handler="lambda_function.lambda_handler",
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            layers=[yfinance_layer]
        )

        # Create Bedrock Agent role
        agent_role = iam.Role(
            self, "RiskManagerAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Risk Manager Bedrock Agent"
        )

        # Add required permissions for the agent role
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[self.risk_manager_function.function_arn]
            )
        )

        # Create Bedrock Agent
        self.risk_manager_agent = aws_bedrock.CfnAgent(
            self, "RiskManagerAgent",
            agent_name="risk_manager",
            agent_resource_role_arn=agent_role.role_arn,
            description="Risk management expert agent for portfolio risk analysis",
            instruction="You are a risk management expert. You must perform risk analysis on the given portfolio and provide portfolio adjustment guides according to major economic scenarios.\n\nInput Data:\nThe proposed portfolio composition is provided in the following JSON format:\n{\n  \"portfolio_allocation\": {\n    \"ticker1\": ratio1,\n    \"ticker2\": ratio2,\n    \"ticker3\": ratio3\n  },\n  \"strategy\": \"investment strategy explanation\",\n  \"reason\": \"portfolio composition rationale\"\n}\n\nYour Tasks:\nUse the given tools freely to achieve the following objectives:\n1. Comprehensive risk analysis of the given portfolio\n2. Derive 2 highly probable economic scenarios\n3. Propose portfolio adjustment measures for each scenario\n\nProvide the final results in the following JSON format:\n{\n  \"scenario1\": {\n    \"name\": \"Scenario 1 name\",\n    \"description\": \"Scenario 1 detailed description\",\n    \"allocation_management\": {\n      \"ticker1\": new_ratio1,\n      \"ticker2\": new_ratio2,\n      \"ticker3\": new_ratio3\n    },\n    \"reason\": \"adjustment reason and strategy\"\n  },\n  \"scenario2\": {\n    \"name\": \"Scenario 2 name\",\n    \"description\": \"Scenario 2 detailed description\",\n    \"allocation_management\": {\n      \"ticker1\": new_ratio1,\n      \"ticker2\": new_ratio2,\n      \"ticker3\": new_ratio3\n    },\n    \"reason\": \"adjustment reason and strategy\"\n  }\n}\n\nPlease strictly follow these requirements when responding:\n1. Only use products (tickers) received as input when adjusting the portfolio.\n2. Do not add new products or remove existing products.\n3. Explain the portfolio composition rationale in detail.",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0"
        )

        # Construct agent ARN
        agent_arn = Fn.sub(
            "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent/${AgentId}",
            {"AgentId": self.risk_manager_agent.attr_agent_id}
        )

        # Add Lambda permission for Bedrock Agent
        self.risk_manager_function.add_permission(
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
                agentName='risk_manager',
                agentResourceRoleArn=event['ResourceProperties']['AgentRoleArn'],
                agentConfiguration={
                    'actionGroups': [{
                        'name': 'action-group-risk-manager',
                        'description': 'Action group for risk manager functions',
                        'actionGroupExecutor': {
                            'lambda': {
                                'functionArn': event['ResourceProperties']['LambdaArn'],
                                'functionVersion': 'LATEST'
                            }
                        },
                        'actions': [
                            {
                                'name': 'get_product_news',
                                'description': 'Gets news for the selected investment product.',
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
                                'name': 'get_market_data',
                                'description': 'Gets current market data.',
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
                "AgentId": self.risk_manager_agent.attr_agent_id,
                "AgentRoleArn": agent_role.role_arn,
                "LambdaArn": self.risk_manager_function.function_arn
            }
        )

        # Make sure the custom resource depends on the agent
        update_agent.node.add_dependency(self.risk_manager_agent)

        # Create a custom resource to create and prepare the agent alias
        prepare_alias_provider = cr.Provider(
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
                agentAliasName='risk-manager-demo',
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
        )

        # Create the custom resource using the provider
        prepare_alias = CustomResource(
            self, "PrepareAgentAlias",
            service_token=prepare_alias_provider.service_token,
            properties={
                "AgentId": self.risk_manager_agent.attr_agent_id
            }
        )

        # Make sure the alias preparation happens after the agent update
        prepare_alias.node.add_dependency(update_agent)

        # Output the Lambda function ARN
        CfnOutput(
            self, "RiskManagerFunctionArn",
            value=self.risk_manager_function.function_arn,
            description="ARN of the Risk Manager Lambda function"
        )

        # Output the Lambda function name
        CfnOutput(
            self, "RiskManagerFunctionName",
            value=self.risk_manager_function.function_name,
            description="Name of the Risk Manager Lambda function"
        )

        # Output the Bedrock Agent ID
        CfnOutput(
            self, "RiskManagerAgentId",
            value=self.risk_manager_agent.attr_agent_id,
            description="ID of the Risk Manager Bedrock Agent"
        )

        # Output the Bedrock Agent ARN
        CfnOutput(
            self, "RiskManagerAgentArn",
            value=agent_arn,
            description="ARN of the Risk Manager Bedrock Agent"
        )
