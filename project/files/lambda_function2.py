import json
import yfinance as yf


def get_named_parameter(event, name):
    for param in event['parameters']:
        if param['name'] == name:
            return param['value']
    return None


def get_product_news(ticker, top_n=5):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:top_n]

        formatted_news = []
        for item in news:
            content = item.get("content", "")
            news_item = {
                "title": content.get("title", ""),
                "summary": content.get("summary", ""),
                "publish_date": content.get("pubDate", "")[:10]
            }
            formatted_news.append(news_item)

        result = {
            "ticker": ticker,
            "news": formatted_news,
        }

        return result

    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return {"error": str(e)}


def get_market_data():
    try:
        market_info = {
            "us_dollar_index": {"ticker": "DX-Y.NYB", "description": "US Dollar Strength Index"},
            "us_10y_treasury_yield": {"ticker": "^TNX", "description": "US 10-Year Treasury Yield (%)"},
            "us_2y_treasury_yield": {"ticker": "2YY=F", "description": "US 2-Year Treasury Yield (%)"},
            "vix_volatility_index": {"ticker": "^VIX", "description": "VIX Index indicating market volatility"},
            "crude_oil_price": {"ticker": "CL=F", "description": "WTI Crude Oil Futures Price (USD/barrel)"}
        }

        data = {}
        for key, info in market_info.items():
            ticker = yf.Ticker(info["ticker"])
            market_price = ticker.info.get('regularMarketPreviousClose', 0)

            data[key] = {
                "description": info["description"],
                "value": round(market_price, 2)
            }

        return data

    except Exception as e:
        print(f"Error fetching market data: {e}")
        return {"error": str(e)}


def lambda_handler(event, context):
    action_group = event.get('actionGroup', '')
    message_version = event.get('messageVersion', '')
    function = event.get('function', '')

    if function == 'get_product_news':
        ticker = get_named_parameter(event, "ticker")
        output = get_product_news(ticker)
    elif function == 'get_market_data':
        output = get_market_data()
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
    print("Response: {}".format(json.dumps(function_response, ensure_ascii=False)))

    return function_response