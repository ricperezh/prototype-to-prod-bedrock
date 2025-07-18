# CDK App Testing Guide

This guide covers how to test your Financial Analysis CDK application.

## ✅ Test Results Summary

All tests are currently **PASSING** ✅

- **Unit Tests**: 9/9 passed
- **CDK Synthesis**: ✅ Success
- **Stack Validation**: ✅ Success
- **Environment Check**: ✅ Ready

## Testing Commands

### 1. Unit Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_financial_analysis_stack.py -v

# Run with coverage
python -m pytest tests/ --cov=project --cov-report=html
```

### 2. CDK Validation
```bash
# Synthesize CloudFormation templates
cdk synth

# List all stacks
cdk list

# Check environment
cdk doctor

# Compare with deployed stack (after deployment)
cdk diff FinancialAnalysisStack
```

### 3. Pre-Deployment Validation
```bash
# Full validation pipeline
cdk synth FinancialAnalysisStack
python -m pytest tests/ -v
```

## Test Coverage

### FinancialAnalysisStack Tests
- ✅ S3 bucket creation and configuration
- ✅ Lambda layer with correct properties
- ✅ Both Bedrock prompts (analyst + reflection)
- ✅ Correct AI models (Nova Pro + Claude 3.5)
- ✅ S3 deployment configuration
- ✅ All stack outputs
- ✅ Resource count validation
- ✅ Inference configurations

### What Each Test Validates

1. **test_s3_bucket_created**: Verifies S3 bucket with versioning and correct naming
2. **test_lambda_layer_created**: Validates yfinance layer properties
3. **test_bedrock_prompts_created**: Ensures both prompts exist
4. **test_bedrock_prompt_models**: Confirms correct AI models are used
5. **test_s3_deployment_created**: Validates file deployment setup
6. **test_stack_outputs**: Checks all required outputs are present
7. **test_resource_count**: Verifies expected number of resources
8. **test_bedrock_prompt_inference_config**: Validates AI model parameters

## Deployment Testing

### 1. Bootstrap (First time only)
```bash
cdk bootstrap
```

### 2. Deploy to Test Environment
```bash
# Deploy with confirmation
cdk deploy FinancialAnalysisStack

# Deploy without confirmation (CI/CD)
cdk deploy FinancialAnalysisStack --require-approval never
```

### 3. Post-Deployment Validation
```bash
# Check what was deployed
aws s3 ls | grep agenticai
aws lambda list-layers --query 'Layers[?LayerName==`yfinance-layer`]'
aws bedrock list-prompts --query 'promptSummaries[?name==`financial_analyst`]'
```

### 4. Integration Testing
```bash
# Test S3 file access
aws s3 ls s3://your-bucket-name/data/

# Test Bedrock prompt
aws bedrock invoke-model \
  --model-id amazon.nova-pro-v1:0 \
  --body '{"prompt": "test"}' \
  output.json
```

## Cleanup Testing
```bash
# Remove deployed resources
cdk destroy FinancialAnalysisStack
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: CDK Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest
      - run: python -m pytest tests/ -v
      - run: cdk synth
```

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure virtual environment is activated
2. **CDK Synthesis Fails**: Check Python syntax and imports
3. **Test Failures**: Verify stack properties match expectations
4. **Deployment Issues**: Check AWS credentials and permissions

### Debug Commands
```bash
# Verbose CDK output
cdk synth --verbose

# Debug specific test
python -m pytest tests/unit/test_financial_analysis_stack.py::test_s3_bucket_created -v -s

# Check CDK context
cat cdk.context.json
```

## Best Practices

1. **Run tests before every commit**
2. **Test in isolated environment first**
3. **Validate CloudFormation templates**
4. **Check resource costs before deployment**
5. **Clean up test resources after testing**

## Next Steps

After successful testing:
1. Commit your changes
2. Deploy to development environment
3. Run integration tests
4. Deploy to production (if ready)
