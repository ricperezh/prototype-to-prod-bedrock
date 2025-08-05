from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_bedrock as bedrock,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
import random
import string
import json


class FinancialAnalysisStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Generate random identifier for S3 bucket
        # random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        # bucket_name = f"agenticai-{random_id}"

        # Create S3 bucket
        self.s3_bucket = s3.Bucket(
            self, "AgenticAIBucket",
            bucket_name="agenticai-131289",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # Use RETAIN for production
            auto_delete_objects=True  # Use False for production
        )

        # Deploy files to S3 bucket
        self.s3_deployment = s3deploy.BucketDeployment(
            self, "S3FilesDeployment",
            sources=[s3deploy.Source.asset("files")],  # Deploy all files from the files directory
            destination_bucket=self.s3_bucket,
            memory_limit=1024,  # Increase memory limit to 1024 MB
            prune=False,  # Don't delete files that aren't in the source
            retain_on_delete=False  # Files will be deleted when stack is destroyed
        )

        # Create Lambda Layer for yfinance
        self.yfinance_layer = _lambda.LayerVersion(
            self, "YFinanceLayer",
            layer_version_name="yfinance-layer",
            code=_lambda.Code.from_asset("files/yfinance.zip"),  # Custom upload path
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            compatible_architectures=[_lambda.Architecture.X86_64],
            license="Apache License 2.0",
            description="Lambda layer containing yfinance library for financial data analysis"
        )

        # Define the financial analyst prompt text
        financial_analyst_prompt = """You are a financial analysis expert. Based on the given user information, you should evaluate risk propensity and calculate required annual return rate to output financial analysis results.

User information is provided in the following JSON format:
{
  "total_investable_amount": <total investable amount>,
  "age": <age>,
  "stock_investment_experience_years": <years of stock investment experience>,
  "target_amount": <target amount after one year>
}

Actual user information:
{{user_input}}

Consider the following when analyzing:
1. Risk Propensity Assessment:
- Comprehensively evaluate risk propensity considering age, investment experience, financial status, and target amount
2. Required Annual Return Rate Calculation:
- Clearly show calculation process step by step and explain each step
- Briefly interpret the meaning of the calculated return rate

Based on this information, output the analysis results in JSON format as follows:
{
  "risk_profile": "Risk propensity assessment (choose one from: Very Conservative, Conservative, Neutral, Aggressive, Very Aggressive)",
  "risk_profile_reason": "Detailed explanation of risk propensity assessment",
  "required_annual_return_rate": Required annual return rate (percentage to two decimal places),
  "return_rate_reason": "Detailed explanation of required annual return rate calculation process and its meaning"
}

Note the following when outputting:
- Do not include additional explanations or text
- Output pure JSON format without backticks (```) or quotes around the JSON"""

        # Define the financial analyst reflection prompt text
        financial_analyst_reflection_prompt = """You are an expert reviewing financial analysis results. You must evaluate the appropriateness of the analysis based on the given financial analysis results.

The financial analysis results are provided in the following JSON format:
{
  "risk_profile": <risk propensity assessment>,
  "risk_profile_reason": <detailed explanation of risk propensity assessment>,
  "required_annual_return_rate": <required annual return rate>,
  "return_rate_reason": <explanation of required annual return rate calculation process and its meaning>
}

Actual financial analysis results:
{{finance_result}}

Review the financial analysis results based on the following criteria:
1. Review by repeating the required annual return rate calculation process
2. Verify if the calculated return rate is within the 0%~50% range

Output format:
- If the calculation is correct AND the return rate is 50% or below, output only "yes" without any additional explanation.
- If the calculation is incorrect OR the return rate exceeds 50%, output "no" followed by a brief explanation on the next line."""

        # Create Bedrock Prompt for financial analysis
        self.financial_analyst_prompt = bedrock.CfnPrompt(
            self, "FinancialAnalystPrompt",
            name="financial_analyst",
            description="Financial analysis expert prompt for risk assessment and return rate calculation",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="TEXT",
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                            text=financial_analyst_prompt,
                            input_variables=[
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="user_input"
                                )
                            ]
                        )
                    ),
                    model_id="amazon.nova-pro-v1:0",
                    inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                        text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                            temperature=0.2,
                            top_p=0.9,
                            max_tokens=2000
                        )
                    )
                )
            ]
        )

        cfn_prompt_version = bedrock.CfnPromptVersion(self, "FinancialAnalystPromptVersion",
            prompt_arn=self.financial_analyst_prompt.attr_arn,

        )

        # Create Bedrock Prompt for financial analysis reflection
        self.financial_analyst_reflection_prompt = bedrock.CfnPrompt(
            self, "FinancialAnalystReflectionPrompt",
            name="financial_analyst_reflection",
            description="Expert prompt for reviewing and validating financial analysis results",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="TEXT",
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                            text=financial_analyst_reflection_prompt,
                            input_variables=[
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="finance_result"
                                )
                            ]
                        )
                    ),
                    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                    inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                        text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                            temperature=0.2,
                            top_p=0.999,
                            max_tokens=2000
                        )
                    )
                )
            ]
        )

        cfn_prompt_version = bedrock.CfnPromptVersion(self, "FinancialAnalystReflectionPromptVersion",
            prompt_arn=self.financial_analyst_reflection_prompt.attr_arn,

        )

        # Output the bucket name, layer ARN, and prompt details
        CfnOutput(
            self, "S3BucketName",
            value=self.s3_bucket.bucket_name,
            description="Name of the S3 bucket for AgenticAI"
        )

        CfnOutput(
            self, "YFinanceLayerArn",
            value=self.yfinance_layer.layer_version_arn,
            description="ARN of the yfinance Lambda layer"
        )

        CfnOutput(
            self, "FinancialAnalystPromptId",
            value=self.financial_analyst_prompt.attr_id,
            description="ID of the Bedrock financial analyst prompt"
        )

        CfnOutput(
            self, "FinancialAnalystPromptArn",
            value=self.financial_analyst_prompt.attr_arn,
            description="ARN of the Bedrock financial analyst prompt"
        )

        CfnOutput(
            self, "FinancialAnalystReflectionPromptId",
            value=self.financial_analyst_reflection_prompt.attr_id,
            description="ID of the Bedrock financial analyst reflection prompt"
        )

        CfnOutput(
            self, "FinancialAnalystReflectionPromptArn",
            value=self.financial_analyst_reflection_prompt.attr_arn,
            description="ARN of the Bedrock financial analyst reflection prompt"
        )

        # CfnOutput(
        #     self, "S3DeploymentOneARN",
        #     value=self.s3_deployment.attr_arn,
        #     description="Status of S3 file deployment"
        # )

        # CfnOutput(
        #     self, "S3DeploymentTwoARN",
        #     value=self.s3_deployment_lambda.attr_arn,
        #     description="Status of S3 file deployment"
        # )
