#!/usr/bin/env python3
import os

import aws_cdk as cdk

from project.project_stack import ProjectStack
from project.financialAnalysisStack import FinancialAnalysisStack
from project.portfolioArchitect import PortfolioArchitectStack


app = cdk.App()

# Original project stack
ProjectStack(app, "ProjectStack")

# Financial Analysis stack with S3 bucket and Lambda layer
FinancialAnalysisStack(app, "FinancialAnalysisStack")

# Portfolio Architect stack with Lambda function
PortfolioArchitectStack(app, "PortfolioArchitectStack")

app.synth()
