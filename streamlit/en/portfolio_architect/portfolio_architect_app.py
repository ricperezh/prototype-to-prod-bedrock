import portfolio_architect_lib as plib
import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import uuid

# Config
PORTFOLIO_ARCHITECT_AGENT_ID = ""
PORTFOLIO_ARCHITECT_AGENT_ALIAS_ID = ""


# Functions
def display_available_products(trace_container, trace):
    """Display available investment products in table format"""
    products_text = trace.get('observation', {}).get('actionGroupInvocationOutput', {}).get('text')
    products = json.loads(products_text)
    
    df = pd.DataFrame(
        [[ticker, str(desc)] for ticker, desc in products.items()],
        columns=['Ticker', 'Description']
    )
    
    trace_container.markdown("**Available Investment Products**")
    trace_container.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn(width="small"),
            "Description": st.column_config.TextColumn(width="large")
        }
    )

def display_product_data(trace_container, trace):
    """Display price history charts for investment products"""
    data_text = trace.get('observation', {}).get('actionGroupInvocationOutput', {}).get('text')
    data = json.loads(data_text)
    
    for ticker, prices in data.items():
        if isinstance(prices, dict) and prices:
            df = pd.DataFrame.from_dict(prices, orient='index', columns=['Price'])
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
        else:
            trace_container.write(f"No valid price data available for {ticker}")
            continue
        
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Price'],
                mode='lines',
                name=ticker,
                line=dict(width=2)
            )
        )
        
        fig.update_layout(
            title=f"{ticker} Price Trend",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=400,
            showlegend=True,
            hovermode='x unified'
        )
        
        trace_container.plotly_chart(fig, use_container_width=True)

def create_pie_chart(data, chart_title=""):
    """Create a pie chart for portfolio allocation"""
    if isinstance(data, str):
        data = json.loads(data)
    
    fig = go.Figure(data=[go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    
    fig.update_layout(
        title=chart_title,
        showlegend=True,
        width=400,
        height=400
    )
    return fig

def display_portfolio_suggestion(place_holder, input_content):
    """Display portfolio suggestion results"""
    data = json.loads(input_content, strict=False)
    sub_col1, sub_col2 = place_holder.columns([1, 1])
    
    with sub_col1:
        st.markdown("**Portfolio**")
        portfolio_allocation = data["portfolio_allocation"]
        if isinstance(portfolio_allocation, str):
            portfolio_allocation = json.loads(portfolio_allocation)
        fig = create_pie_chart(
            portfolio_allocation,
            "Portfolio Asset Allocation"
        )
        st.plotly_chart(fig)
    
    with sub_col2:
        st.markdown("**Investment Strategy**")
        st.info(data["strategy"])
    
    place_holder.markdown("**Detailed Rationale**")
    place_holder.write(data["reason"])

# Page setup
st.set_page_config(page_title="Portfolio Architect")

st.title("🤖 Portfolio Architect")

with st.expander("Architecture", expanded=True):
    st.image(os.path.join("../../dataset/images/portfolio_architect.png"))

# Input form
st.markdown("**Enter Financial Analysis Results (🤖 Financial Analyst)**")

financial_analysis = st.text_area(
    "JSON format",
    height=200
)

submitted = st.button("Start Analysis", use_container_width=True)

if submitted and financial_analysis:
    st.divider()
    placeholder = st.container()
    
    with st.spinner("AI is processing..."):
        response = plib.get_agent_response(
            PORTFOLIO_ARCHITECT_AGENT_ID,
            PORTFOLIO_ARCHITECT_AGENT_ALIAS_ID,
            str(uuid.uuid4()),
            financial_analysis
        )
        
        placeholder.subheader("Bedrock Reasoning")
        
        output_text = ""
        function_name = ""
        
        for event in response.get("completion"):
            if "chunk" in event:
                chunk = event["chunk"]
                output_text += chunk["bytes"].decode()
            
            if "trace" in event:
                each_trace = event["trace"]["trace"]
                
                if "orchestrationTrace" in each_trace:
                    trace = event["trace"]["trace"]["orchestrationTrace"]
                    
                    if "rationale" in trace:
                        with placeholder.chat_message("ai"):
                            st.markdown(trace['rationale']['text'])
                    
                    elif function_name != "":
                        if function_name == "get_available_products":
                            display_available_products(placeholder, trace)
                        elif function_name == "get_product_data":
                            display_product_data(placeholder, trace)
                        
                        function_name = ""
                    
                    else:
                        function_name = trace.get('invocationInput', {}).get('actionGroupInvocationInput', {}).get(
                            'function', "")
        
        placeholder.divider()
        placeholder.markdown("🤖 **Portfolio Architect**")
        placeholder.subheader("📌 Portfolio Design")
        display_portfolio_suggestion(placeholder, output_text)