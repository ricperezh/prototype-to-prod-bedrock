import os
import json
import yfinance as yf
import boto3
from datetime import datetime, timedelta


s3 = boto3.client('s3')


def get_named_parameter(event, name):
    # Get the value of a specific parameter from the Lambda event
    for param in event['parameters']:
        if param['name'] == name:
            return param['value']
    return None


def get_available_products():
    bucket_name = os.environ['S3_BUCKET_NAME']
    file_name = 'available_products_en.json'
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        content = response['Body'].read().decode('utf-8')
        products = json.loads(content)
        return products
    
    except Exception as e:
        print(f"Error reading from S3: {e}")
        return {"error": str(e)}


def get_product_data(ticker):
    try:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=100)

        product_data = {}
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)

        # Store closing prices for each asset
        product_data[ticker] = {
            date.strftime('%Y-%m-%d'): round(price, 2) for date, price in hist['Close'].items()
        }

        return product_data

    except Exception as e:
        print(f"Error fetching asset prices: {e}")
        return {"error": str(e)}


def lambda_handler(event, context):
    action_group = event.get('actionGroup', '')
    message_version = event.get('messageVersion', '')
    function = event.get('function', '')

    if function == 'get_available_products':
        output = get_available_products()
    elif function == 'get_product_data':
        ticker = get_named_parameter(event, "ticker")
        output = get_product_data(ticker)
    else:
        output = 'Invalid function'

    action_response = {
        'actionGroup': action_group,
        'function': function,
        'functionResponse': {
            'responseBody': {'TEXT': {'body': json.dumps(output, ensure_ascii=False)}}
        }
    }

    function_response = {'response': action_response, 'messageVersion': message_version}
    print("Response: {}".format(function_response, ensure_ascii=False))

    return function_response