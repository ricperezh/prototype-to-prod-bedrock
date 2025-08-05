#!/usr/bin/env python3
import os

import aws_cdk as cdk

from project.financialAnalysisStack import FinancialAnalysisStack
from project.portfolioArchitect import PortfolioArchitectStack
from project.riskManagerStack import RiskManagerStack
from project.investmentAdvisorStack import InvestmentAdvisorStack


app = cdk.App()

# Financial Analysis stack with S3 bucket and Lambda layer
financial_analysis_stack = FinancialAnalysisStack(app, "FinancialAnalysisStack")

# Portfolio Architect stack with Lambda function
portfolio_architect_stack = PortfolioArchitectStack(app, "PortfolioArchitectStack", yfinance_layer=financial_analysis_stack.yfinance_layer)

# Risk Manager stack with Lambda function
risk_manager_stack = RiskManagerStack(app, "RiskManagerStack", yfinance_layer=financial_analysis_stack.yfinance_layer)

# Investment Advisor stack with Bedrock prompt
InvestmentAdvisorStack(app, "InvestmentAdvisorStack", financial_analyst_prompt_arn= financial_analysis_stack.financial_analyst_prompt.attr_arn, financial_analyst_reflection_prompt_arn= financial_analysis_stack.financial_analyst_reflection_prompt.attr_arn, portfolio_architect_agent_id= portfolio_architect_stack.portfolio_architect_agent.attr_agent_id , risk_manager_agent_id= risk_manager_stack.risk_manager_agent.attr_agent_id, portfolio_architect_agent_alias_id= portfolio_architect_stack.portfolio_architect_agent_alias.attr_agent_alias_id ,risk_manager_agent_alias_id= risk_manager_stack.risk_manager_agent_alias.attr_agent_alias_id)

app.synth()
