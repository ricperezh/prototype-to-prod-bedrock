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

    def __init__(self, scope: Construct, construct_id: str, yfinance_layer: _lambda.ILayerVersion, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket name from FinancialAnalysisStack
        s3_bucket_name = "agenticai-131289"

        # Create Lambda execution role with basic permissions
        lambda_role = iam.Role(
            self, "PortfolioArchitectRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
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
            layers=[yfinance_layer],
            environment={
                "S3_BUCKET_NAME": s3_bucket_name
            }
        )

        # Create IAM role for the agent
        agent_role = iam.Role(
            self, "PortfolioArchitectRoleAgent",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Portfolio Architect Bedrock Agent"
        )

        # Add required permissions for the agent role
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:*"
                ],
                resources=[self.portfolio_architect_function.function_arn]
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

        self.portfolio_architect_agent = aws_bedrock.CfnAgent(
            self, "PortfolioArchitectAgent",
            agent_name="portfolio_architect",
            description="portfolio_architect",
            agent_resource_role_arn=agent_role.role_arn,
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            instruction="""You are a professional investment designer. You must propose a specific investment portfolio based on the client's financial analysis results.

        Input Data:
        Financial analysis results are provided in the following JSON format:
        {
        "risk_profile": <risk propensity>,
        "risk_profile_reason": <risk propensity assessment basis>,
        "required_annual_return_rate": <required annual return rate>,
        "return_rate_reason": <required return rate calculation basis and explanation>
        }

        Your Tasks:
        1. Carefully review and interpret the financial analysis results.
        2. Call the "get_available_products" action to get a list of available investment products. Each product is provided in "ticker: description" format.
        3. Select the 3 most suitable products from the obtained product list considering diversification and the client's financial analysis results.
        4. Call the "get_product_data" action simultaneously for each selected investment product to get recent price data.
        5. Analyze the obtained price data to determine final portfolio ratios. Consider the client's financial analysis results in a balanced way.
        6. Explain the portfolio composition rationale in detail.

        Please respond in the following JSON format:
        {
        "portfolio_allocation": {investment product allocation ratios} (e.g., {"ticker1": 50, "ticker2": 30, "ticker3": 20}),
        "strategy": "investment strategy explanation",
        "reason": "portfolio composition rationale"
        }

        Consider the following when responding:
        - Logically explain how the proposed portfolio will help achieve the client's investment goals.
        - Asset allocation ratios must be expressed as integers and total 100%.
        - When writing the portfolio composition rationale, always provide both ticker and description like "QQQ(US Technology Stocks)".""",
            action_groups=[
                aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="action-group-portfolio-architect",
                    description="action-group-portfolio-architect",
                    action_group_executor=aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.portfolio_architect_function.function_arn
                    ),
                    function_schema=aws_bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            aws_bedrock.CfnAgent.FunctionProperty(
                                name="get_product_data",
                                description="Gets recent price data for the selected investment product.",
                                parameters={
                                    "ticker": aws_bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Ticker of the investment product to look up",
                                        required=True
                                    )
                                },
                                require_confirmation="DISABLED"
                            ),
                            aws_bedrock.CfnAgent.FunctionProperty(
                                name="get_available_products",
                                description="Gets list of available investment products.",
                                require_confirmation="DISABLED"
                            )
                        ]
                    )
                )
            ]
        )

        self.portfolio_architect_agent_alias = aws_bedrock.CfnAgentAlias(self, "PortfolioArchitectAgentAlias",
            agent_alias_name="portfolio-architect-demo",
            agent_id=self.portfolio_architect_agent.attr_agent_id,
            description="portfolio-architect-demo"
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

        # Add resource-based policy to allow Bedrock agent to invoke Lambda
        self.portfolio_architect_function.add_permission(
            "allow-bedrock-agent",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/{self.portfolio_architect_agent.attr_agent_id}"
        )
        
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
        # CfnOutput(
        #     self, "PortfolioArchitectAgentArn",
        #     value=self.portfolio_architect_agent.attr_arn,
        #     description="ARN of the Portfolio Architect Bedrock Agent"
        # )
