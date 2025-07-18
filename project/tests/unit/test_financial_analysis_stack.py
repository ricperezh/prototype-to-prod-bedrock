import aws_cdk as core
import aws_cdk.assertions as assertions
from project.financialAnalysisStack import FinancialAnalysisStack


def test_s3_bucket_created():
    """Test that S3 bucket is created with correct properties"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check S3 bucket exists
    template.has_resource_properties("AWS::S3::Bucket", {
        "VersioningConfiguration": {
            "Status": "Enabled"
        }
    })

    # Check bucket name starts with "agenticai-"
    template.has_resource_properties("AWS::S3::Bucket", 
        assertions.Match.object_like({
            "BucketName": assertions.Match.string_like_regexp("^agenticai-.*")
        })
    )


def test_lambda_layer_created():
    """Test that Lambda layer is created with correct properties"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check Lambda layer exists
    template.has_resource_properties("AWS::Lambda::LayerVersion", {
        "LayerName": "yfinance-layer",
        "CompatibleRuntimes": ["python3.12"],
        "CompatibleArchitectures": ["x86_64"],
        "LicenseInfo": "Apache License 2.0"
    })


def test_bedrock_prompts_created():
    """Test that both Bedrock prompts are created"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check financial analyst prompt
    template.has_resource_properties("AWS::Bedrock::Prompt", {
        "Name": "financial_analyst",
        "DefaultVariant": "default"
    })

    # Check financial analyst reflection prompt
    template.has_resource_properties("AWS::Bedrock::Prompt", {
        "Name": "financial_analyst_reflection",
        "DefaultVariant": "default"
    })


def test_bedrock_prompt_models():
    """Test that Bedrock prompts use correct models"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check Nova Pro model is used
    template.has_resource_properties("AWS::Bedrock::Prompt",
        assertions.Match.object_like({
            "Variants": assertions.Match.array_with([
                assertions.Match.object_like({
                    "ModelId": "amazon.nova-pro-v1:0"
                })
            ])
        })
    )

    # Check Claude model is used
    template.has_resource_properties("AWS::Bedrock::Prompt",
        assertions.Match.object_like({
            "Variants": assertions.Match.array_with([
                assertions.Match.object_like({
                    "ModelId": "anthropic.claude-3-5-sonnet-20241022-v2:0"
                })
            ])
        })
    )


def test_s3_deployment_created():
    """Test that S3 deployment is configured"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check S3 deployment custom resource exists
    template.has_resource_properties("Custom::CDKBucketDeployment", {
        "DestinationBucketKeyPrefix": "data/"
    })


def test_stack_outputs():
    """Test that all required outputs are present"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check all outputs exist
    template.has_output("S3BucketName", {})
    template.has_output("YFinanceLayerArn", {})
    template.has_output("FinancialAnalystPromptId", {})
    template.has_output("FinancialAnalystPromptArn", {})
    template.has_output("FinancialAnalystReflectionPromptId", {})
    template.has_output("FinancialAnalystReflectionPromptArn", {})
    template.has_output("S3DeploymentStatus", {})


def test_resource_count():
    """Test that expected number of resources are created"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check we have the expected resources
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.resource_count_is("AWS::Lambda::LayerVersion", 2)  # yfinance + AWS CLI layer
    template.resource_count_is("AWS::Bedrock::Prompt", 2)


def test_bedrock_prompt_inference_config():
    """Test Bedrock prompt inference configurations"""
    app = core.App()
    stack = FinancialAnalysisStack(app, "test-stack")
    template = assertions.Template.from_stack(stack)

    # Check Nova Pro configuration
    template.has_resource_properties("AWS::Bedrock::Prompt",
        assertions.Match.object_like({
            "Name": "financial_analyst",
            "Variants": assertions.Match.array_with([
                assertions.Match.object_like({
                    "InferenceConfiguration": {
                        "Text": {
                            "Temperature": 0.2,
                            "TopP": 0.9,
                            "MaxTokens": 2000
                        }
                    }
                })
            ])
        })
    )

    # Check Claude configuration
    template.has_resource_properties("AWS::Bedrock::Prompt",
        assertions.Match.object_like({
            "Name": "financial_analyst_reflection",
            "Variants": assertions.Match.array_with([
                assertions.Match.object_like({
                    "InferenceConfiguration": {
                        "Text": {
                            "Temperature": 0.2,
                            "TopP": 0.999,
                            "MaxTokens": 2000
                        }
                    }
                })
            ])
        })
    )
