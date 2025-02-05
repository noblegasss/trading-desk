import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import yfinance as yf
import datetime
import pytz

app = dash.Dash(__name__)
server = app.server
app.title = "Real-Time Stock Dashboard"
eastern_tz = pytz.timezone('US/Eastern')

def adjust_to_trading_day(date_str):
    dt = pd.to_datetime(date_str).date()
    weekday = dt.weekday()
    if weekday == 5:  # Saturday
        dt -= datetime.timedelta(days=1)
    elif weekday == 6:  # Sunday
        dt -= datetime.timedelta(days=2)
    return dt

def fetch_stock_data(ticker, start_date, end_date, interval='1d'):
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    # Increase end date by one day to include the final day
    end_dt += pd.Timedelta(days=1)

    start_dt = start_dt.strftime('%Y-%m-%d')
    end_dt = end_dt.strftime('%Y-%m-%d')
    
    data = yf.download(
        ticker, 
        start=start_dt, 
        end=end_dt, 
        interval=interval,
        prepost=True  # Fetch both pre and post market data
    )
    
    if not data.empty:
        data.reset_index(inplace=True)
        # Rename 'Datetime' to 'Date' for consistency
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
    return data

def add_moving_average(df, window, col_name_prefix="MA"):
    df[f"{col_name_prefix}_{window}"] = df['Close'].rolling(window=window, min_periods=1).mean()
    return df



app.layout = html.Div([
    html.H1("Real-Time Stock Dashboard", style={'textAlign': 'center'}),
    html.Div([
        # Left side: Input controls and stock info
        html.Div([
            html.H3("Inputs"),
            html.Div([
                html.Label("Enter Stock Symbols (comma-separated):"),
                dcc.Input(
                    id='ticker-input',
                    value='AAPL, MSFT, TSLA, QQQ, NVDA',
                    type='text',
                    style={'marginRight': '10px', 'width': '300px'}
                )
            ], style={'padding': '10px'}),
            
            html.Div([
                html.Label("Select Date Range:"),
                dcc.DatePickerRange(
                    id='date-range',
                    min_date_allowed=datetime.date(2000, 1, 1),
                    max_date_allowed=datetime.datetime.now(eastern_tz).date(),
                    start_date=datetime.datetime.now(eastern_tz).date(),
                    end_date=datetime.datetime.now(eastern_tz).date()
                )
            ], style={'padding': '10px'}),
            
            html.Div([
                html.Label("Short-Term MA Window:"),
                dcc.Input(
                    id='short-ma',
                    value='20',
                    type='number',
                    min=1,
                    style={'marginRight': '20px', 'width': '80px'}
                )
            ], style={'padding': '10px'}),
            
            html.Div([
                html.Label("Long-Term MA Window:"),
                dcc.Input(
                    id='long-ma',
                    value='50',
                    type='number',
                    min=1,
                    style={'width': '80px'}
                )
            ], style={'padding': '10px'}),
            
            html.Div([
                html.Label("Auto-Refresh Interval (minutes):"),
                dcc.Input(
                    id='refresh-interval',
                    value=1,  # Default set to 1 minute
                    type='number',
                    min=1,
                    step=1,
                    style={'marginRight': '20px', 'width': '80px'}
                )
            ], style={'padding': '10px'}),
            
            # Radio buttons to control auto-refresh
            html.Div([
                html.Label("Auto-Refresh Control:"),
                dcc.RadioItems(
                    id='auto-refresh-toggle',
                    options=[
                        {'label': 'Start Auto Refresh', 'value': 'start'},
                        {'label': 'Stop Auto Refresh', 'value': 'stop'}
                    ],
                    value='start',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ], style={'padding': '10px'}),
            
            html.Div([
                html.Button(id='submit-button', n_clicks=0, children='Update Dashboard')
            ], style={'padding': '10px'}),
            
            html.H3("Stock Information"),
            html.Div(id='stock-info', style={'padding': '10px'})
        ], style={
            'width': '30%', 'display': 'inline-block',
            'verticalAlign': 'top', 'padding': '10px', 'borderRight': '1px solid #ccc'
        }),
        
        # Right side: Stock charts
        html.Div(id='stock-charts', style={
            'width': '65%', 'display': 'inline-block',
            'padding': '10px', 'verticalAlign': 'top'
        })
    ]),
    
    # Interval component for auto-refresh (default: 1 minute)
    dcc.Interval(
        id='refresh-interval-component',
        interval=60000,  # 1 minute = 60000 milliseconds
        n_intervals=0
    )
])

# Callback to update the interval time (in minutes)
@app.callback(
    Output('refresh-interval-component', 'interval'),
    [Input('refresh-interval', 'value')]
)
def update_refresh_interval(interval_minutes):
    if interval_minutes is None or interval_minutes < 1:
        return 60000
    return int(interval_minutes) * 60000

# Callback to enable/disable auto-refresh based on radio button selection
@app.callback(
    Output('refresh-interval-component', 'disabled'),
    [Input('auto-refresh-toggle', 'value')]
)
def toggle_autorefresh(auto_refresh_value):
    return True if auto_refresh_value == 'stop' else False

# Main callback to update charts and stock information
@app.callback(
    [Output('stock-charts', 'children'),
     Output('stock-info', 'children')],
    [Input('submit-button', 'n_clicks'),
     Input('refresh-interval-component', 'n_intervals')],
    [State('ticker-input', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date'),
     State('short-ma', 'value'),
     State('long-ma', 'value')]
)
def update_dashboard(n_clicks, n_intervals, tickers, start_date, end_date, short_ma, long_ma):
    if not tickers:
        return [], "No tickers provided."
    
    # Adjust dates to the nearest trading day
    adjusted_start = adjust_to_trading_day(start_date)
    adjusted_end = adjust_to_trading_day(end_date)
    start_dt = pd.to_datetime(adjusted_start)
    end_dt = pd.to_datetime(adjusted_end)
    days_diff = (end_dt - start_dt).days

    # Use a 1-minute interval (and time tick labels) when the range is under 5 days;
    # otherwise, use daily data with full date tick labels.
    if days_diff < 5:
        interval = '1m'
        xaxis_format = '%H:%M'  # Only time displayed
        xaxis_title = 'Time'
    else:
        interval = '1d'
        xaxis_format = '%Y-%m-%d'
        xaxis_title = 'Date'

    ticker_list = [ticker.strip().upper() for ticker in tickers.split(',')]
    stock_charts = []
    stock_info_html = []
    colors = ['blue', 'green', 'orange', 'purple', 'brown', 'magenta', 'cyan', 'grey']
    
    for i, ticker in enumerate(ticker_list):
        try:
            df = fetch_stock_data(ticker, start_dt, end_dt, interval)
            if df.empty:
                continue
            
            # Use the appropriate date column
            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            
            # Calculate moving averages
            short_window = int(short_ma) if short_ma else 20
            long_window = int(long_ma) if long_ma else 50
            df = add_moving_average(df, short_window, "Short_MA")
            df = add_moving_average(df, long_window, "Long_MA")

            # Get the current time and current stock price from the latest data point
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_price = df['Close'].iloc[-1]
            
            color = colors[i % len(colors)]
            price_trace = go.Scatter(
                x=df[date_col], 
                y=df['Close'], 
                mode='lines',
                name=f"{ticker} Price",
                line=dict(color=color)
            )
            short_ma_trace = go.Scatter(
                x=df[date_col],
                y=df[f"Short_MA_{short_window}"],
                mode='lines',
                name=f"{ticker} Short MA ({short_window})",
                line=dict(color=color, dash='dash')
            )
            long_ma_trace = go.Scatter(
                x=df[date_col],
                y=df[f"Long_MA_{long_window}"],
                mode='lines',
                name=f"{ticker} Long MA ({long_window})",
                line=dict(color=color, dash='dot')
            )
            
            # Build the layout with the updated title including last update time and current price
            layout = go.Layout(
                title=dict(
                    text=f"{ticker} Stock Price<br><sub>Last Updated: {current_time} | Current Price: ${current_price:.2f}</sub>",
                    x=0.05,
                    xanchor='left'
                ),
                xaxis=dict(
                    title=xaxis_title,
                    tickformat=xaxis_format,
                    rangebreaks=[
                        dict(bounds=["sat", "mon"]),  # Hide weekends
                        dict(bounds=[20, 4], pattern="hour")  # Hide overnight hours
                    ],
                    type='date'
                ),
                yaxis=dict(title='Price (USD)'),
                hovermode='x unified',
                margin=dict(t=60)  # Extra top margin for the title
            )
            
            stock_charts.append(dcc.Graph(
                id=f'graph-{ticker}', 
                figure={'data': [price_trace, short_ma_trace, long_ma_trace], 'layout': layout}
            ))
            
            # Fetch additional stock information via yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            info_table = html.Table([
                html.Tr([html.Th("Attribute"), html.Th("Value")]),
                html.Tr([html.Td("Name"), html.Td(info.get('longName', 'N/A'))]),
                html.Tr([html.Td("Sector"), html.Td(info.get('sector', 'N/A'))]),
                html.Tr([html.Td("Market Cap"), html.Td(f"${info.get('marketCap', 0):,}")]),
                html.Tr([html.Td("Previous Close"), html.Td(info.get('previousClose', 'N/A'))]),
                html.Tr([html.Td("Open"), html.Td(info.get('open', 'N/A'))]),
                html.Tr([html.Td("High"), html.Td(info.get('dayHigh', 'N/A'))]),
                html.Tr([html.Td("Low"), html.Td(info.get('dayLow', 'N/A'))]),
                html.Tr([html.Td("Volume"), html.Td(f"{info.get('volume', 0):,}")]),
                html.Tr([html.Td("Average Volume"), html.Td(f"{info.get('averageVolume', 0):,}")]),
                html.Tr([html.Td("52 Week High"), html.Td(info.get('fiftyTwoWeekHigh', 'N/A'))]),
                html.Tr([html.Td("52 Week Low"), html.Td(info.get('fiftyTwoWeekLow', 'N/A'))]),
                html.Tr([html.Td("PE Ratio"), html.Td(info.get('trailingPE', 'N/A'))])
            ], style={'border': '1px solid black', 'margin-bottom': '20px', 'width': '300px'})
            
            stock_info_html.append(
                html.Div([
                    html.H4(f"Stock Info for {ticker}"),
                    info_table
                ], style={'display': 'inline-block', 'margin': '10px', 'verticalAlign': 'top'})
            )
        except Exception as e:
            stock_info_html.append(
                html.Div([html.H4(f"Error fetching info for {ticker}: {str(e)}")])
            )
    
    return stock_charts, stock_info_html

if __name__ == '__main__':
    # app.run_server(debug=True, host='0.0.0.0', port=8080)
    app.run_server(debug=True)
