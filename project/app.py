#!/usr/bin/env python3
import os

import aws_cdk as cdk

from project.project_stack import ProjectStack
from project.financialAnalysisStack import FinancialAnalysisStack
from project.portfolioArchitect import PortfolioArchitectStack
from project.riskManagerStack import RiskManagerStack


app = cdk.App()

# Original project stack
ProjectStack(app, "ProjectStack")

# Financial Analysis stack with S3 bucket and Lambda layer
financial_analysis_stack = FinancialAnalysisStack(app, "FinancialAnalysisStack")

# Portfolio Architect stack with Lambda function
PortfolioArchitectStack(app, "PortfolioArchitectStack")

# Risk Manager stack with Lambda function
RiskManagerStack(app, "RiskManagerStack", yfinance_layer=financial_analysis_stack.yfinance_layer)

app.synth()
