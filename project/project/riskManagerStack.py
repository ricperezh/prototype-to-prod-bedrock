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
        
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=["*"]
            )
        )

        # Create the Bedrock Agent
        self.risk_manager_agent = aws_bedrock.CfnAgent(
            self, "RiskManagerAgent",
            agent_name="risk_manager",
            description="risk_manager",
            agent_resource_role_arn=agent_role.role_arn,
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            instruction="""You are a risk management expert. You must perform risk analysis on the given portfolio and provide portfolio adjustment guides according to major economic scenarios.

Input Data:
The proposed portfolio composition is provided in the following JSON format:
{
  "portfolio_allocation": {
    "ticker1": ratio1,
    "ticker2": ratio2,
    "ticker3": ratio3
  },
  "strategy": "investment strategy explanation",
  "reason": "portfolio composition rationale"
}

Your Tasks:
Use the given tools freely to achieve the following objectives:
1. Comprehensive risk analysis of the given portfolio
2. Derive 2 highly probable economic scenarios
3. Propose portfolio adjustment measures for each scenario

Provide the final results in the following JSON format:
{
  "scenario1": {
    "name": "Scenario 1 name",
    "description": "Scenario 1 detailed description",
    "allocation_management": {
      "ticker1": new_ratio1,
      "ticker2": new_ratio2,
      "ticker3": new_ratio3
    },
    "reason": "adjustment reason and strategy"
  },
  "scenario2": {
    "name": "Scenario 2 name",
    "description": "Scenario 2 detailed description",
    "allocation_management": {
      "ticker1": new_ratio1,
      "ticker2": new_ratio2,
      "ticker3": new_ratio3
    },
    "reason": "adjustment reason and strategy"
  }
}

Please strictly follow these requirements when responding:
1. Only use products (tickers) received as input when adjusting the portfolio.
2. Do not add new products or remove existing products.
3. Explain the portfolio composition rationale in detail.""",
            
            action_groups=[
                aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="action-group-risk-manager",
                    description="action-group-risk-manager",
                    action_group_executor=aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.risk_manager_function.function_arn
                    ),
                    action_group_state="ENABLED",
                    function_schema=aws_bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            aws_bedrock.CfnAgent.FunctionProperty(
                                name="get_product_news",
                                description="Gets recent news for the selected investment product.",
                                require_confirmation="DISABLED",
                                parameters={
                                    "ticker": aws_bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Ticker of the investment product to look up",
                                        required=True
                                    )
                                }
                            )
                        ]
                    )
                )
            ]
        )

        self.risk_manager_agent_alias = aws_bedrock.CfnAgentAlias(self, "RiskManagerAgentAlias",
            agent_alias_name="risk-manager-demo",
            agent_id=self.risk_manager_agent.attr_agent_id,
            description="risk-manager-demo"
        )

        # Add resource-based policy to allow Bedrock agent to invoke Lambda
        self.risk_manager_function.add_permission(
            "allow-bedrock-agent",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/{self.risk_manager_agent.attr_agent_id}"
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
        # CfnOutput(
        #     self, "RiskManagerAgentArn",
        #     value=agent_arn,
        #     description="ARN of the Risk Manager Bedrock Agent"
        # )
