from aws_cdk import (
    Stack,
    aws_bedrock,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class InvestmentAdvisorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, financial_analyst_prompt_arn: str, financial_analyst_reflection_prompt_arn: str, portfolio_architect_agent_id: str , risk_manager_agent_id: str , portfolio_architect_agent_alias_id: str, risk_manager_agent_alias_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the report generator prompt text
        report_generator_prompt = """You are a professional investment advisor. You must create an investment portfolio analysis report based on the given information.

Input Data:
User Information:
{{user_input}}
Financial Analysis Results:
{{finance_result}}
Proposed Portfolio Composition:
{{portfolio_result}}
Portfolio Adjustment Guide:
{{risk_result}}

Please analyze all the above information comprehensively and create an analysis report strictly following this format:

### Investment Portfolio Analysis Report
#### 1. Client Profile Analysis
- Name: John Doe
- Address: 123 Wall Street, New York, NY
- Contact: (123) 456-7890
- [User Information]
#### 2. Basic Portfolio Composition
##### Asset Allocation
- [ETF Ticker] ([ETF Description]): [Allocation Ratio]%
##### Allocation Strategy Rationale
- [Explanation of Allocation Strategy]
#### 3. Scenario-based Response Strategies
##### Scenario: [Scenario 1]
Adjusted Asset Allocation:
- [ETF Ticker]: [New Ratio]% ([Change Amount])
Response Strategy:
- [Response Strategy]
#### 4. Precautions and Recommendations
- [Precautions and Recommendations]
#### 5. Conclusion
[Comprehensive Conclusion and Recommendations on Portfolio Strategy]

Consider the following when writing:
1. Clearly mention investment risks.
2. Provide customized advice for the client's specific situation.
3. Include a brief legal disclaimer at the end of the report."""

        # Create Bedrock Prompt for report generation
        self.report_generator_prompt = aws_bedrock.CfnPrompt(
            self, "ReportGeneratorPrompt",
            name="report_generator",
            description="Investment portfolio analysis report generator prompt",
            default_variant="default",
            variants=[
                aws_bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="TEXT",
                    template_configuration=aws_bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        text=aws_bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                            text=report_generator_prompt,
                            input_variables=[
                                aws_bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="user_input"
                                ),
                                aws_bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="finance_result"
                                ),
                                aws_bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="portfolio_result"
                                ),
                                aws_bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="risk_result"
                                )
                            ]
                        )
                    ),
                    model_id="anthropic.claude-3-haiku-20240307-v1:0",
                    inference_configuration=aws_bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                        text=aws_bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                            temperature=0.3,
                            top_p=0.999,
                            max_tokens=2000
                        )
                    )
                )
            ]
        )

        # Create Bedrock Guardrail
        aws_bedrock.CfnGuardrail(
            self, "ReportGeneratorGuardrail",
            name="report-generator-guardrails",
            blocked_input_messaging="Sorry, the model cannot answer this question.",
            blocked_outputs_messaging="Sorry, the model cannot answer this question.",
            sensitive_information_policy_config=aws_bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "ADDRESS"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "AGE"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "NAME"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "EMAIL"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "PHONE"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "USERNAME"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "PASSWORD"),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                    action="ANONYMIZE",
                    type = "LICENSE_PLATE")
                ]
            )
        )
        # Create IAM role for the flow
        flow_role = iam.Role(
            self, "InvestmentAdvisorFlowRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com")
        )

        flow_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel", "bedrock:InvokePrompt", "bedrock:GetPrompt", "bedrock:InvokeAgent"],
                resources=["*"]
            )
        )

        cfn_flow = aws_bedrock.CfnFlow(
            self, "InvestmentAdvisorFlow",
            name="investment_advisor",
            description="investment_advisor",
            execution_role_arn=flow_role.role_arn,
            definition=aws_bedrock.CfnFlow.FlowDefinitionProperty(
                nodes=[
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="start",
                        type="Input",
                        outputs=[
                            aws_bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="document",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="FinancialAnalyst",
                        type="Prompt",
                        configuration=aws_bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            prompt=aws_bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                                source_configuration=aws_bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                                    resource=aws_bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                                        prompt_arn=financial_analyst_prompt_arn
                                    )
                                )
                            )
                        ),
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="user_input",
                                type="String"
                            )
                        ],
                        outputs=[
                            aws_bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="modelCompletion",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="FinancialAnalystReflection",
                        type="Prompt",
                        configuration=aws_bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            prompt=aws_bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                                source_configuration=aws_bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                                    resource=aws_bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                                        prompt_arn=financial_analyst_reflection_prompt_arn
                                    )
                                )
                            )
                        ),
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="finance_result",
                                type="String"
                            )
                        ],
                        outputs=[
                            aws_bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="modelCompletion",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="end1",
                        type="Output",
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="document",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="ReflectionCondition",
                        type="Condition",
                        configuration=aws_bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            condition=aws_bedrock.CfnFlow.ConditionFlowNodeConfigurationProperty(
                                conditions=[
                                    aws_bedrock.CfnFlow.FlowConditionProperty(
                                        name="condition",
                                        expression="conditionInput == \"yes\""
                                    ),
                                    aws_bedrock.CfnFlow.FlowConditionProperty(
                                        name="default"
                                    )
                                ]
                            )
                        ),
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="conditionInput",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="PortfolioArchitect",
                        type="Agent",
                        configuration=aws_bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            agent=aws_bedrock.CfnFlow.AgentFlowNodeConfigurationProperty(
                                agent_alias_arn= f"arn:aws:bedrock:{self.region}:{self.account}:agent-alias/{portfolio_architect_agent_id}/{portfolio_architect_agent_alias_id}"
                            )
                        ),
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="agentInputText",
                                type="String"
                            )
                        ],
                        outputs=[
                            aws_bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="agentResponse",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="RiskManager",
                        type="Agent",
                        configuration=aws_bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            agent=aws_bedrock.CfnFlow.AgentFlowNodeConfigurationProperty(
                                agent_alias_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent-alias/{risk_manager_agent_id}/{risk_manager_agent_alias_id}"
                            )
                        ),
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="agentInputText",
                                type="String"
                            )
                        ],
                        outputs=[
                            aws_bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="agentResponse",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="ReportGenerator",
                        type="Prompt",
                        configuration=aws_bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            prompt=aws_bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                                source_configuration=aws_bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                                    resource=aws_bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                                        prompt_arn= self.report_generator_prompt.attr_arn
                                    )
                                )
                            )
                        ),
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="user_input",
                                type="String"
                            ),
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="finance_result",
                                type="String"
                            ),
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="portfolio_result",
                                type="String"
                            ),
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="risk_result",
                                type="String"
                            )
                        ],
                        outputs=[
                            aws_bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="modelCompletion",
                                type="String"
                            )
                        ]
                    ),
                    aws_bedrock.CfnFlow.FlowNodeProperty(
                        name="end",
                        type="Output",
                        inputs=[
                            aws_bedrock.CfnFlow.FlowNodeInputProperty(
                                expression="$.data",
                                name="document",
                                type="String"
                            )
                        ]
                    )
                ],
                connections=[
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cStart",
                        source="start",
                        target="FinancialAnalyst",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="document",
                                target_input="user_input"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cFinancialAnalyst",
                        source="FinancialAnalyst",
                        target="FinancialAnalystReflection",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="modelCompletion",
                                target_input="finance_result"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cFinancialAnalystReflection",
                        source="FinancialAnalystReflection",
                        target="ReflectionCondition",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="modelCompletion",
                                target_input="conditionInput"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cFinancialAnalystReflection2",
                        source="FinancialAnalystReflection",
                        target="end1",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="modelCompletion",
                                target_input="document"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cReflectionConditionTrue",
                        source="ReflectionCondition",
                        target="PortfolioArchitect",
                        type="Conditional",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            conditional=aws_bedrock.CfnFlow.FlowConditionalConnectionConfigurationProperty(
                                condition="condition"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cReflectionConditionFalse",
                        source="ReflectionCondition",
                        target="end1",
                        type="Conditional",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            conditional=aws_bedrock.CfnFlow.FlowConditionalConnectionConfigurationProperty(
                                condition="default"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cFinancialAnalystToPortfolio",
                        source="FinancialAnalyst",
                        target="PortfolioArchitect",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="modelCompletion",
                                target_input="agentInputText"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cPortfolioToRisk",
                        source="PortfolioArchitect",
                        target="RiskManager",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="agentResponse",
                                target_input="agentInputText"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cStartToReport",
                        source="start",
                        target="ReportGenerator",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="document",
                                target_input="user_input"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cFinancialToReport",
                        source="FinancialAnalyst",
                        target="ReportGenerator",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="modelCompletion",
                                target_input="finance_result"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cPortfolioToReport",
                        source="PortfolioArchitect",
                        target="ReportGenerator",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="agentResponse",
                                target_input="portfolio_result"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cRiskToReport",
                        source="RiskManager",
                        target="ReportGenerator",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="agentResponse",
                                target_input="risk_result"
                            )
                        )
                    ),
                    aws_bedrock.CfnFlow.FlowConnectionProperty(
                        name="cReportToEnd",
                        source="ReportGenerator",
                        target="end",
                        type="Data",
                        configuration=aws_bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=aws_bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="modelCompletion",
                                target_input="document"
                            )
                        )
                    )
                ]
            )
        )

        cfn_flow_version = aws_bedrock.CfnFlowVersion(self, "InvestmentAdvisorFlowVersion",
            flow_arn=cfn_flow.attr_arn,
        )

        cfn_flow_alias = aws_bedrock.CfnFlowAlias(self, "InvestmentAdvisorFlowAlias",
            flow_arn= cfn_flow.attr_arn,
            name="investment-advisor-demo",
            routing_configuration=[aws_bedrock.CfnFlowAlias.FlowAliasRoutingConfigurationListItemProperty(
                flow_version= cfn_flow_version.attr_version
            )]
        )
        
        cfn_flow_alias.add_dependency(cfn_flow_version)

        


        # Output the Bedrock Prompt ID and ARN
        CfnOutput(
            self, "ReportGeneratorPromptId",
            value=self.report_generator_prompt.attr_id,
            description="ID of the report generator Bedrock prompt"
        )

        CfnOutput(
            self, "ReportGeneratorPromptArn",
            value=self.report_generator_prompt.attr_arn,
            description="ARN of the report generator Bedrock prompt"
        )

        # # Output the Bedrock Guardrail ID and ARN
        # CfnOutput(
        #     self, "ReportGeneratorGuardrailId",
        #     value=self.report_generator_guardrail.attr_guardrail_id,
        #     description="ID of the report generator Bedrock guardrail"
        # )

        # CfnOutput(
        #     self, "ReportGeneratorGuardrailArn",
        #     value=self.report_generator_guardrail.attr_guardrail_arn,
        #     description="ARN of the report generator Bedrock guardrail"
        # )
