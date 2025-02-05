import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import yfinance as yf
import datetime
import pytz
import dash_daq as daq

app = dash.Dash(__name__)
server = app.server
app.title = "Real-Time Stock Dashboard"

# Custom color scheme
colors = {
    'background': '#f4f6fa',
    'header': '#1f77b4',
    'card-background': 'white',
    'text': '#2c3e50',
    'positive': '#27ae60',
    'negative': '#e74c3c'
}

eastern_tz = pytz.timezone('US/Eastern')

def adjust_to_trading_day(date_str):
    dt = pd.to_datetime(date_str).date()
    weekday = dt.weekday()
    # If weekend, adjust to previous Friday
    if weekday == 5:  # Saturday
        dt -= datetime.timedelta(days=1)
    elif weekday == 6:  # Sunday
        dt -= datetime.timedelta(days=2)
    return dt

def fetch_stock_data(ticker, start_date, end_date, interval='1d'):
    eastern_tz = pytz.timezone('US/Eastern')
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    data = yf.download(
        ticker,
        start=start_dt.strftime('%Y-%m-%d'),
        end=end_dt.strftime('%Y-%m-%d'),
        interval=interval,
        prepost=True
    )
    
    if not data.empty:
        data.reset_index(inplace=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
        
        # Convert to datetime
        data['Date'] = pd.to_datetime(data['Date'])
        if interval == '1m':
            # If timestamps have no timezone, localize them to UTC
            if data['Date'].dt.tz is None:
                data['Date'] = data['Date'].dt.tz_localize('UTC')

            # Convert to Eastern timezone
            data['Date'] = data['Date'].dt.tz_convert(eastern_tz)

 
    return data


def add_moving_average(df, window, col_name_prefix="MA"):
    df[f"{col_name_prefix}_{window}"] = df['Close'].rolling(window=window, min_periods=1).mean()
    return df

app.layout = html.Div(
    style={'backgroundColor': colors['background'], 'minHeight': '100vh'},
    children=[
        html.Header(
            style={
                'backgroundColor': colors['header'],
                'padding': '2rem',
                'marginBottom': '2rem',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            },
            children=[
                html.H1(
                    "Real-Time Stock Dashboard",
                    style={
                        'color': 'white',
                        'textAlign': 'center',
                        'margin': 0,
                        'fontWeight': '600'
                    }
                ),
                html.Div(
                    "Interactive Financial Analytics Platform",
                    style={
                        'color': 'rgba(255,255,255,0.9)',
                        'textAlign': 'center',
                        'marginTop': '0.5rem'
                    }
                )
            ]
        ),
        html.Div(
            style={
                'display': 'flex',
                'gap': '2rem',
                'padding': '0 2rem',
                'maxWidth': '1600px',
                'margin': '0 auto'
            },
            children=[
                # Left sidebar
                html.Div(
                    style={
                        'width': '320px',
                        'flexShrink': 0,
                        'backgroundColor': colors['card-background'],
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                    },
                    children=[
                        html.Div(
                            [
                                html.Label(
                                    "Stock Symbols",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600',
                                        'color': colors['text']
                                    }
                                ),
                                dcc.Input(
                                    id='ticker-input',
                                    value='AAPL, MSFT, TSLA, QQQ, NVDA',
                                    type='text',
                                    style={
                                        'width': '95%',
                                        'padding': '0.75rem',
                                        'border': '1px solid #ddd',
                                        'borderRadius': '8px',
                                        'fontSize': '1rem'
                                    }
                                )
                            ],
                            style={'marginBottom': '1.5rem'}
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Date Range",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600',
                                        'color': colors['text']
                                    }
                                ),
                                dcc.DatePickerRange(
                                    id='date-range',
                                    min_date_allowed=datetime.date(2000, 1, 1),
                                    max_date_allowed=datetime.datetime.now(eastern_tz).date(),
                                    start_date=datetime.datetime.now(eastern_tz).date(),
                                    end_date=datetime.datetime.now(eastern_tz).date(),
                                    style={'width': '100%'}
                                )
                            ],
                            style={'marginBottom': '1.5rem'}
                        ),
                        html.Div(
                            style={'display': 'flex', 'gap': '1rem', 'marginBottom': '1.5rem'},
                            children=[
                                html.Div(
                                    style={'flex': 1},
                                    children=[
                                        html.Label(
                                            "Short MA",
                                            style={
                                                'display': 'block',
                                                'marginBottom': '0.5rem',
                                                'fontWeight': '600',
                                                'color': colors['text']
                                            }
                                        ),
                                        dcc.Input(
                                            id='short-ma',
                                            value='20',
                                            type='number',
                                            min=1,
                                            style={
                                                'width': '100%',
                                                'padding': '0.5rem',
                                                'border': '1px solid #ddd',
                                                'borderRadius': '6px'
                                            }
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={'flex': 1},
                                    children=[
                                        html.Label(
                                            "Long MA",
                                            style={
                                                'display': 'block',
                                                'marginBottom': '0.5rem',
                                                'fontWeight': '600',
                                                'color': colors['text']
                                            }
                                        ),
                                        dcc.Input(
                                            id='long-ma',
                                            value='50',
                                            type='number',
                                            min=1,
                                            style={
                                                'width': '100%',
                                                'padding': '0.5rem',
                                                'border': '1px solid #ddd',
                                                'borderRadius': '6px'
                                            }
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            style={'marginBottom': '1.5rem'},
                            children=[
                                html.Label(
                                    "Auto-Refresh Settings",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600',
                                        'color': colors['text']
                                    }
                                ),
                                html.Div(
                                    style={
                                        'display': 'flex',
                                        'gap': '1rem',
                                        'alignItems': 'center'
                                    },
                                    children=[
                                        dcc.Input(
                                            id='refresh-interval',
                                            value=1,
                                            type='number',
                                            min=1,
                                            style={
                                                'flex': 1,
                                                'padding': '0.5rem',
                                                'border': '1px solid #ddd',
                                                'borderRadius': '6px'
                                            }
                                        ),
                                        daq.ToggleSwitch(
                                            id='auto-refresh-toggle',
                                            value=True,
                                            color="#1f77b4",
                                            labelPosition='bottom'
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Button(
                            id='submit-button',
                            n_clicks=0,
                            children='Update Dashboard',
                            style={
                                'width': '100%',
                                'padding': '1rem',
                                'backgroundColor': colors['header'],
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '8px',
                                'cursor': 'pointer',
                                'fontSize': '1rem',
                                'transition': 'background-color 0.2s'
                            }
                        )
                    ]
                ),
                # Main content area with Tabs
                html.Div(
                    style={'flexGrow': 1, 'minWidth': '0'},
                    children=[
                        dcc.Tabs(
                            id="tabs",
                            value='tab-charts',
                            children=[
                                dcc.Tab(
                                    label='Charts',
                                    value='tab-charts',
                                    children=[
                                        dcc.Loading(
                                            id="loading-charts",
                                            type="circle",
                                            children=[
                                                html.Div(
                                                    id='stock-charts',
                                                    style={
                                                        'display': 'grid',
                                                        'gap': '2rem',
                                                        'gridTemplateColumns': 'repeat(auto-fit, minmax(600px, 1fr))'
                                                    }
                                                )
                                            ]
                                        )
                                    ]
                                ),
                                dcc.Tab(
                                    label='Stock Info',
                                    value='tab-info',
                                    children=[
                                        html.Div(
                                            id='stock-info',
                                            style={
                                                'marginTop': '2rem',
                                                'display': 'grid',
                                                'gap': '1.5rem',
                                                'gridTemplateColumns': 'repeat(auto-fill, minmax(300px, 1fr))'
                                            }
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        dcc.Interval(
            id='refresh-interval-component',
            interval=60000,
            n_intervals=0
        )
    ]
)

@app.callback(
    Output('refresh-interval-component', 'interval'),
    [Input('refresh-interval', 'value')]
)
def update_refresh_interval(interval_minutes):
    if interval_minutes is None or interval_minutes < 1:
        return 60000
    return int(interval_minutes) * 60000

@app.callback(
    Output('refresh-interval-component', 'disabled'),
    [Input('auto-refresh-toggle', 'value')]
)
def toggle_autorefresh(auto_refresh_enabled):
    return not auto_refresh_enabled

def format_number(value):
    if pd.isna(value):
        return 'N/A'
    if value >= 1e12:
        return f'${value/1e12:.2f}T'
    if value >= 1e9:
        return f'${value/1e9:.2f}B'
    if value >= 1e6:
        return f'${value/1e6:.2f}M'
    return f'${value:,.2f}'

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
        return [], []
    
    adjusted_start = adjust_to_trading_day(start_date)
    adjusted_end = adjust_to_trading_day(end_date)
    start_dt = pd.to_datetime(adjusted_start)
    end_dt = pd.to_datetime(adjusted_end)
    days_diff = (end_dt - start_dt).days

    # Decide on interval for intraday vs daily
    interval = '15m' if days_diff >= 5 else '1m'
    xaxis_format = '%H:%M' if days_diff < 5 else '%Y-%m-%d'
    xaxis_title = 'Time' if days_diff < 5 else 'Date'

    ticker_list = [ticker.strip().upper() for ticker in tickers.split(',')]
    stock_charts = []
    stock_info_html = []
    
    for i, ticker in enumerate(ticker_list):
        try:
            df = fetch_stock_data(ticker, start_dt, end_dt, interval)
            if df.empty:
                continue

            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            short_window = int(short_ma) if short_ma else 20
            long_window = int(long_ma) if long_ma else 50
            df = add_moving_average(df, short_window, "Short_MA")
            df = add_moving_average(df, long_window, "Long_MA")

            current_time = datetime.datetime.now(eastern_tz).strftime('%Y-%m-%d %H:%M:%S')
            current_price = df['Close'].iloc[-1]
            
            # Create main price chart
            price_chart = go.Scatter(
                x=df[date_col],
                y=df['Close'],
                mode='lines',
                name='Price',
                line=dict(color='#1f77b4', width=1.5)
            )
            
            ma_short = go.Scatter(
                x=df[date_col],
                y=df[f'Short_MA_{short_window}'],
                mode='lines',
                name=f'MA {short_window}',
                line=dict(color='#ff7f0e', dash='dash')
            )
            
            ma_long = go.Scatter(
                x=df[date_col],
                y=df[f'Long_MA_{long_window}'],
                mode='lines',
                name=f'MA {long_window}',
                line=dict(color='#2ca02c', dash='dot')
            )
            
            # Create volume chart
            volume_bars = go.Bar(
                x=df[date_col],
                y=df['Volume'],
                name='Volume',
                marker_color='#a1a1a1',
                yaxis='y2'
            )

            fig = go.Figure(data=[price_chart, ma_short, ma_long, volume_bars])
            
            # Update layout
            fig.update_layout(
                title=f'{ticker} Stock Analysis<br><sub>Last Updated: {current_time} | Current Price: ${current_price:.2f}</sub>',
                xaxis=dict(
                    title=xaxis_title,
                    rangeslider=dict(visible=False),
                    # Move range selector slightly lower (y=1.05 instead of 1.2)
                    rangeselector=dict(
                        buttons=[
                            dict(step='all', label='All'),
                            dict(count=1, label='1H', step='hour', stepmode='backward'),
                            dict(count=2, label='2H', step='hour', stepmode='backward'),
                            dict(count=6, label='6H', step='hour', stepmode='backward')
                        ],
                        x=1,
                        xanchor='right',
                        y=1.1,
                        yanchor='top'
                    ),
                    rangebreaks=[
                        dict(bounds=["sat", "mon"]),  # Hide weekends
                        dict(bounds=[20, 4], pattern="hour")  # Hide overnight hours
                    ],
                    type='date'
                ),
                yaxis=dict(title='Price', domain=[0.3, 1]),
                yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False),
                hovermode='x unified',
                template='plotly_white',
                # Make the chart a bit taller
                height=500,
                # Increase bottom margin so the legend doesn't get cut off
                margin=dict(t=100, r=80, b=20),
                # Legend below x-axis
                legend=dict(
                    orientation='h',
                    x=0.5,
                    y=0,        # negative y places it below the x-axis
                    xanchor='center',
                    yanchor='top'
                )
            )
            
            stock_charts.append(dcc.Graph(figure=fig))
            
            # Stock information
            stock = yf.Ticker(ticker)
            info = stock.info
            info_items = [
                ('Current Price', format_number(current_price)),
                ('Previous Close', format_number(info.get('previousClose'))),
                ('Open', format_number(info.get('open'))),
                ('Day Range', f"{info.get('dayLow', 'N/A')} - {info.get('dayHigh', 'N/A')}"),
                ('52 Week Range', f"{info.get('fiftyTwoWeekLow', 'N/A')} - {info.get('fiftyTwoWeekHigh', 'N/A')}"),
                ('Volume', f"{info.get('volume', 0):,}"),
                ('Market Cap', format_number(info.get('marketCap'))),
                ('PE Ratio', f"{info.get('trailingPE', 'N/A')}"),
                ('Dividend Yield', (
                    f"{info.get('dividendYield', 'N/A')*100:.2f}%"
                    if info.get('dividendYield') else 'N/A'
                ))
            ]
            
            info_card = html.Div(
                style={
                    'backgroundColor': colors['card-background'],
                    'borderRadius': '10px',
                    'padding': '1.5rem',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                },
                children=[
                    html.H4(ticker, style={'marginTop': 0, 'color': colors['header']}),
                    html.Div([
                        html.Div(
                            style={
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'padding': '8px 0',
                                'borderBottom': '1px solid #eee'
                            },
                            children=[
                                html.Span(label, style={'fontWeight': '500'}),
                                html.Span(value)
                            ]
                        ) for label, value in info_items
                    ])
                ]
            )
            
            stock_info_html.append(info_card)
            
        except Exception as e:
            stock_info_html.append(
                html.Div(
                    f"Error loading {ticker}: {str(e)}", 
                    style={'color': colors['negative']}
                )
            )
    
    return stock_charts, stock_info_html

if __name__ == '__main__':
    app.run_server(debug=True)
