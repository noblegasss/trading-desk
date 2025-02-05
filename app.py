import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import dash_table
import numpy as np
import yfinance as yf
import datetime
import pytz
import dash_daq as daq


app = dash.Dash(__name__)
server = app.server
app.title = "Real-Time Stock Dashboard"

# ------------------------------
# Multiple Themes
# ------------------------------
THEMES = {
    'light': {
        'background': '#f4f6fa',
        'header': '#1f77b4',
        'card-background': 'white',
        'text': '#2c3e50',
        'positive': '#27ae60',
        'negative': '#e74c3c'
    },
    'dark': {
        'background': '#2B2B2B',      
        'header': '#3D3D3D',          
        'card-background': '#444444', 
        'text': '#FAFAFA',            
        'positive': '#27ae60',
        'negative': '#e74c3c'
    }
}

eastern_tz = pytz.timezone('US/Eastern')

def adjust_to_trading_day(date_str):
    dt = pd.to_datetime(date_str).date()
    weekday = dt.weekday()
    if weekday == 5:  # Saturday
        dt -= datetime.timedelta(days=1)
    elif weekday == 6:  # Sunday
        dt -= datetime.timedelta(days=2)
    return dt

def fetch_stock_data(ticker, start_date, end_date, interval='1d', prepost=True):
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    data = yf.download(
        ticker,
        start=start_dt.strftime('%Y-%m-%d'),
        end=end_dt.strftime('%Y-%m-%d'),
        interval=interval,
        prepost=prepost  # <--- controlled by toggle
    )
    
    if not data.empty:
        data.reset_index(inplace=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
        
        data['Date'] = pd.to_datetime(data['Date'])
        # If intraday data (like 1m) is naive, localize to UTC, then convert to Eastern
        if interval == '1m':
            if data['Date'].dt.tz is None:
                data['Date'] = data['Date'].dt.tz_localize('UTC')
            data['Date'] = data['Date'].dt.tz_convert(eastern_tz)

    return data

def add_moving_average(df, window, col_name_prefix="MA"):
    df[f"{col_name_prefix}_{window}"] = df['Close'].rolling(window=window, min_periods=1).mean()
    return df

# ----------------------------------
# Main Layout
# ----------------------------------
app.layout = html.Div(
    id='app-container',  # We'll use a callback to update background
    style={'minHeight': '100vh'},
    children=[
        # Header
        html.Header(
            id='header-container',
            style={
                'padding': '2rem',
                'marginBottom': '2rem',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            },
            children=[
                html.H1(
                    "Real-Time Stock Dashboard",
                    id='main-title',
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
                    id='sidebar-output',  # if you want to also theme the sidebar
                    style={
                        'width': '320px',
                        'flexShrink': 0,
                        'backgroundColor': '#ffffff',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                    },
                    children=[
                        # THEME DROPDOWN
                        html.Div([
                            html.Label("Choose a Theme:", 
                                       id = 'theme-label',
                                       style={'fontWeight': '600'}),
                            dcc.Dropdown(
                                id='theme-dropdown',
                                options=[
                                    {'label': 'Light Theme', 'value': 'light'},
                                    {'label': 'Dark Theme', 'value': 'dark'}
                                ],
                                value='light',  # default
                                clearable=False,
                                style={'width': '95%'}
                            )
                        ], style={'marginBottom': '1.5rem'}),

                        dcc.Store(id='theme-store'),

                        html.Div(
                            [
                                html.Label(
                                    "Stock Symbols",
                                    id="stock-symbols-label",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600'
                                    }
                                ),
                                dcc.Input(
                                    id='ticker-input',
                                    value='SPY, AAPL, MSFT, TSLA, GOOGL, NVDA',
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
                                    id="date-range-label",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600'
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
                                            id="short-ma-label",
                                            style={
                                                'display': 'block',
                                                'marginBottom': '0.5rem',
                                                'fontWeight': '600'
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
                                            id="long-ma-label",
                                            style={
                                                'display': 'block',
                                                'marginBottom': '0.5rem',
                                                'fontWeight': '600'
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
                                    id="auto-refresh-label",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600'
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

                        # Toggle for pre/post market
                        html.Div(
                            [
                                html.Label(
                                    "Include Pre/Post Market?",
                                    id="prepost-label",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600'
                                    }
                                ),
                                daq.ToggleSwitch(
                                    id='prepost-toggle',
                                    value=True,  # default: pre/post included
                                    color="#1f77b4",
                                    labelPosition='bottom'
                                )
                            ],
                            style={'marginBottom': '1.5rem'}
                        ),

                        # (NEW) Radio items for Chart Type
                        html.Div(
                            [
                                html.Label(
                                    "Chart Type",
                                    style={
                                        'display': 'block',
                                        'marginBottom': '0.5rem',
                                        'fontWeight': '600'
                                    }
                                ),
                                dcc.RadioItems(
                                    id='chart-type',
                                    options=[
                                        {'label': 'Line', 'value': 'line'},
                                        {'label': 'Candlestick', 'value': 'candle'},
                                    ],
                                    value='line',  # default
                                    style={'marginLeft': '0.5rem'}
                                )
                            ],
                            style={'marginBottom': '1.5rem'}
                        ),

                        html.Button(
                            id='submit-button',
                            n_clicks=0,
                            children='Update Dashboard',
                            style={
                                'width': '100%',
                                'padding': '1rem',
                                'backgroundColor': '#1f77b4',
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
                                ),
                                # NEW: Sector Analysis Tab
                                dcc.Tab(
                                    label='Sector Analysis',
                                    value='tab-sector',
                                    children=[
                                        dcc.Loading(
                                            id="loading-sector",
                                            type="circle",
                                            children=[
                                                html.Div(
                                                    id='sector-analysis-graph',
                                                    style={'padding': '1rem'}
                                                )
                                            ]
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

# ---------------------------
# Callbacks
# ---------------------------
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

# ---------------------------
# 1) Theme Dropdown -> theme-store
# ---------------------------
@app.callback(
    Output('theme-store', 'data'),
    [Input('theme-dropdown', 'value')]
)
def update_theme_store(selected_theme):
    return THEMES[selected_theme]

# ---------------------------
# 2) Apply the theme
# ---------------------------
@app.callback(
    Output('header-container', 'style'),
    [Input('theme-store', 'data')]
)
def update_header_style(theme):
    return {
        'backgroundColor': theme['header'],
        'padding': '2rem',
        'marginBottom': '2rem',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }

@app.callback(
    Output('main-title', 'style'),
    [Input('theme-store', 'data')]
)
def update_main_title_style(theme):
    return {
        'color': theme['text'],
        'textAlign': 'center',
        'margin': 0,
        'fontWeight': '600'
    }

@app.callback(
    Output('app-container', 'style'),
    [Input('theme-store', 'data')]
)
def update_app_container_style(theme):
    return {
        'backgroundColor': theme['background'],
        'minHeight': '100vh'
    }

# Optional: sidebar background
@app.callback(
    Output('sidebar-output', 'style'),
    [Input('theme-store', 'data')]
)
def update_sidebar_style(theme):
    return {
        'backgroundColor': theme['card-background'],
        'borderRadius': '12px',
        'padding': '1.5rem',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }

# Optional: dynamic label text color
@app.callback(
    [
        Output("stock-symbols-label", "style"),
        Output("date-range-label", "style"),
        Output("short-ma-label", "style"),
        Output("long-ma-label", "style"),
        Output("auto-refresh-label", "style"),
        Output("prepost-label", "style")
    ],
    [Input('theme-store', 'data')]
)
def update_label_colors(theme):
    label_style = {
        'display': 'block',
        'marginBottom': '0.5rem',
        'fontWeight': '600',
        'color': theme['text']  # dynamic text color
    }
    return [label_style]*6

# ---------------------------
# 3) Main Dashboard Callback
# ---------------------------
@app.callback(
    [Output('stock-charts', 'children'),
     Output('stock-info', 'children')],
    [
        Input('submit-button', 'n_clicks'),
        Input('refresh-interval-component', 'n_intervals'),
        Input('prepost-toggle', 'value'),   # Toggle for pre/post market
        Input('chart-type', 'value')        # NEW: input for line/candle
    ],
    [
        State('ticker-input', 'value'),
        State('date-range', 'start_date'),
        State('date-range', 'end_date'),
        State('short-ma', 'value'),
        State('long-ma', 'value')
    ]
)
def update_dashboard(n_clicks, n_intervals, prepost, chart_type, 
                     tickers, start_date, end_date, short_ma, long_ma):
    if not tickers:
        return [], []
    
    adjusted_start = adjust_to_trading_day(start_date)
    adjusted_end = adjust_to_trading_day(end_date)
    start_dt = pd.to_datetime(adjusted_start)
    end_dt = pd.to_datetime(adjusted_end)
    days_diff = (end_dt - start_dt).days

    # Decide on intraday vs daily
    interval = '15m' if days_diff >= 5 else '1m'
    xaxis_format = '%H:%M' if days_diff < 5 else '%Y-%m-%d'
    xaxis_title = 'Time' if days_diff < 5 else 'Date'

    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    stock_charts = []
    stock_info_html = []
    
    for ticker in ticker_list:
        try:
            df = fetch_stock_data(ticker, start_dt, end_dt, interval=interval, prepost=prepost)
            if df.empty:
                continue

            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            s_window = int(short_ma) if short_ma else 20
            l_window = int(long_ma) if long_ma else 50

            df = add_moving_average(df, s_window, "Short_MA")
            df = add_moving_average(df, l_window, "Long_MA")

            if prepost:
                rangebreaks = [
                    dict(bounds=["sat", "mon"]),  # Hide weekends
                    dict(bounds=[20, 4], pattern="hour")  # Hide overnight hours
                ]
            else:
                rangebreaks = [
                    dict(bounds=["sat", "mon"]),  # Hide weekends
                    dict(bounds=[16, 9.5], pattern="hour")  # Hide overnight hours
                ]

            current_time = datetime.datetime.now(eastern_tz).strftime('%Y-%m-%d %H:%M:%S')
            current_price = df['Close'].iloc[-1]
            
            # ---------------------------
            # Build the primary chart(s)
            # ---------------------------
            chart_data = []
            
            if chart_type == 'candle':
                # Candlestick chart
                candlestick = go.Candlestick(
                    x=df[date_col],
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name='Price',
                    increasing_line_color='#1f77b4',
                    decreasing_line_color='#ff3333',
                    showlegend=True
                )
                chart_data.append(candlestick)
            else:
                # Line chart
                price_chart = go.Scatter(
                    x=df[date_col],
                    y=df['Close'],
                    mode='lines',
                    name='Price',
                    line=dict(color='#1f77b4', width=1.5)
                )
                chart_data.append(price_chart)

            # Always include moving averages
            ma_short = go.Scatter(
                x=df[date_col],
                y=df[f'Short_MA_{s_window}'],
                mode='lines',
                name=f'MA {s_window}',
                line=dict(color='#ff7f0e', dash='dash')
            )
            
            ma_long = go.Scatter(
                x=df[date_col],
                y=df[f'Long_MA_{l_window}'],
                mode='lines',
                name=f'MA {l_window}',
                line=dict(color='#2ca02c', dash='dot')
            )

            chart_data.extend([ma_short, ma_long])
            
            # Volume on secondary axis
            volume_bars = go.Bar(
                x=df[date_col],
                y=df['Volume'],
                name='Volume',
                marker_color='#a1a1a1',
                yaxis='y2'
            )
            chart_data.append(volume_bars)

            fig = go.Figure(data=chart_data)
            
            fig.update_layout(
                title=f'{ticker} Stock Analysis<br><sub>Last Updated: {current_time} | Current Price: ${current_price:.2f}</sub>',
                xaxis=dict(
                    title=xaxis_title,
                    rangeslider=dict(visible=False),
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
                    rangebreaks=rangebreaks,
                    type='date'
                ),
                yaxis=dict(title='Price', domain=[0.3, 1]),
                yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False),
                hovermode='x unified',
                template='plotly_white',
                height=500,
                margin=dict(t=100, r=80, b=20),
                legend=dict(
                    orientation='h',
                    x=0.5,
                    y=0,
                    xanchor='center',
                    yanchor='top'
                )
            )
            
            stock_charts.append(dcc.Graph(figure=fig))
            
            # ---------------------------
            # Stock info
            # ---------------------------
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
                    'backgroundColor': '#ffffff',
                    'borderRadius': '10px',
                    'padding': '1.5rem',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                },
                children=[
                    html.H4(ticker, style={'marginTop': 0, 'color': '#1f77b4'}),
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
                    style={'color': '#e74c3c'}
                )
            )
    
    return stock_charts, stock_info_html

# ---------------------------
# 4) Sector Analysis Callback (without Subtabs)
# ---------------------------
@app.callback(
    Output('sector-analysis-graph', 'children'),
    [Input('submit-button', 'n_clicks'),
     Input('refresh-interval-component', 'n_intervals')]
)
def update_sector_analysis(n_clicks, n_intervals):
    print("Sector analysis callback triggered")
    # Map each sector to its representative ETF ticker.
    sectors_etfs = {
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financials': 'XLF',
        'Consumer Discretionary': 'XLY',
        'Industrials': 'XLI',
        'Energy': 'XLE',
        'Utilities': 'XLU',
        'Real Estate': 'XLRE',
        'Consumer Staples': 'XLP',
        'Materials': 'XLB'
    }
    
    # Dictionaries to hold computed performance metrics.
    daily_perf = {}
    weekly_perf = {}
    monthly_perf = {}
    quarter_return = {}
    week_range = {}
    month_range = {}
    year_range = {}
    yearly_return = {}
    
    # For correlation matrices: use 1mo and 1y daily closing prices.
    one_month_close = {}
    one_year_close = {}
    
    for sector, etf in sectors_etfs.items():
        try:
            ticker = yf.Ticker(etf)
            info = ticker.info
            
            # Daily performance: current vs previous close.
            current = info.get('regularMarketOpen')
            previous_close = info.get('regularMarketPreviousClose')
            if current is not None and previous_close and previous_close != 0:
                daily = (current - previous_close) / previous_close * 100
            else:
                daily = 0.0
            daily_perf[sector] = daily
            
            # Weekly and monthly performance: use 1mo historical data (daily).
            hist_1mo = ticker.history(period="1mo", interval="1d")
            if hist_1mo.empty:
                weekly_perf[sector] = 0.0
                monthly_perf[sector] = 0.0
            else:
                last_date = hist_1mo.index[-1]
                current_close = hist_1mo["Close"].iloc[-1]
                
                # Weekly performance (~7 days ago).
                desired_weekly = last_date - pd.Timedelta(days=7)
                weekly_rows = hist_1mo[hist_1mo.index <= desired_weekly]
                if not weekly_rows.empty:
                    weekly_close = weekly_rows["Close"].iloc[-1]
                else:
                    weekly_close = hist_1mo["Close"].iloc[0]
                weekly_perf[sector] = (current_close - weekly_close) / weekly_close * 100
                
                # Monthly performance (~30 days ago).
                desired_monthly = last_date - pd.Timedelta(days=30)
                monthly_rows = hist_1mo[hist_1mo.index <= desired_monthly]
                if not monthly_rows.empty:
                    monthly_close_val = monthly_rows["Close"].iloc[-1]
                else:
                    monthly_close_val = hist_1mo["Close"].iloc[0]
                monthly_perf[sector] = (current_close - monthly_close_val) / monthly_close_val * 100
            
            # One-quarter return: use 3mo data.
            hist_3mo = ticker.history(period="3mo", interval="1d")
            if not hist_3mo.empty:
                first_close = hist_3mo["Close"].iloc[0]
                last_close = hist_3mo["Close"].iloc[-1]
                quarter_return[sector] = (last_close - first_close) / first_close * 100
            else:
                quarter_return[sector] = 0.0
            
            # Week range: from 1wk data.
            hist_1wk = ticker.history(period="1wk", interval="1d")
            if not hist_1wk.empty:
                low_val = hist_1wk["Low"].min()
                high_val = hist_1wk["High"].max()
                week_range[sector] = (high_val - low_val) / low_val * 100
            else:
                week_range[sector] = 0.0
            
            # Month range: from 1mo data.
            if not hist_1mo.empty:
                low_val = hist_1mo["Low"].min()
                high_val = hist_1mo["High"].max()
                month_range[sector] = (high_val - low_val) / low_val * 100
            else:
                month_range[sector] = 0.0
            
            # Year range and Yearly return: from 1y data.
            hist_1y = ticker.history(period="1y", interval="1d")
            if not hist_1y.empty:
                low_val = hist_1y["Low"].min()
                high_val = hist_1y["High"].max()
                year_range[sector] = (high_val - low_val) / low_val * 100
                first_close = hist_1y["Close"].iloc[0]
                last_close = hist_1y["Close"].iloc[-1]
                yearly_return[sector] = (last_close - first_close) / first_close * 100
            else:
                year_range[sector] = 0.0
                yearly_return[sector] = 0.0
            
            # For 1-month correlation: fetch 1mo daily data.
            hist_1m_corr = ticker.history(period="1mo", interval="1d")
            if not hist_1m_corr.empty:
                one_month_close[sector] = hist_1m_corr["Close"]
            else:
                one_month_close[sector] = pd.Series([], dtype=float)
            
            # For 1-year correlation: fetch 1y daily data.
            hist_1y_corr = ticker.history(period="1y", interval="1d")
            if not hist_1y_corr.empty:
                one_year_close[sector] = hist_1y_corr["Close"]
            else:
                one_year_close[sector] = pd.Series([], dtype=float)
            
            print(f"{sector} ({etf}): daily={daily_perf[sector]:.2f}%, weekly={weekly_perf[sector]:.2f}%, monthly={monthly_perf[sector]:.2f}%, "
                  f"quarter={quarter_return[sector]:.2f}%, yearlyReturn={yearly_return[sector]:.2f}%, weekRange={week_range[sector]:.2f}%, "
                  f"monthRange={month_range[sector]:.2f}%, yearRange={year_range[sector]:.2f}%")
        except Exception as e:
            print(f"Error fetching data for {etf}: {e}")
            daily_perf[sector] = weekly_perf[sector] = monthly_perf[sector] = quarter_return[sector] = week_range[sector] = month_range[sector] = year_range[sector] = yearly_return[sector] = 0.0
            one_month_close[sector] = pd.Series([], dtype=float)
            one_year_close[sector] = pd.Series([], dtype=float)
    
    # Build bar charts for performance.
    daily_fig = go.Figure(
        data=[go.Bar(
            x=list(daily_perf.keys()),
            y=list(daily_perf.values()),
            marker_color=['#1f77b4' if v >= 0 else '#e74c3c' for v in daily_perf.values()]
        )]
    )
    daily_fig.update_layout(
        title="Daily Performance (%)",
        xaxis_title="Sector",
        yaxis_title="Daily % Change",
        template="plotly_white",
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    weekly_fig = go.Figure(
        data=[go.Bar(
            x=list(weekly_perf.keys()),
            y=list(weekly_perf.values()),
            marker_color=['#1f77b4' if v >= 0 else '#e74c3c' for v in weekly_perf.values()]
        )]
    )
    weekly_fig.update_layout(
        title="Weekly Performance (%)",
        xaxis_title="Sector",
        yaxis_title="Weekly % Change",
        template="plotly_white",
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    monthly_fig = go.Figure(
        data=[go.Bar(
            x=list(monthly_perf.keys()),
            y=list(monthly_perf.values()),
            marker_color=['#1f77b4' if v >= 0 else '#e74c3c' for v in monthly_perf.values()]
        )]
    )
    monthly_fig.update_layout(
        title="Monthly Performance (%)",
        xaxis_title="Sector",
        yaxis_title="Monthly % Change",
        template="plotly_white",
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    # Combine performance graphs side by side.
    graphs_layout = html.Div([
        html.Div(dcc.Graph(figure=daily_fig), style={'flex': '1', 'padding': '10px'}),
        html.Div(dcc.Graph(figure=weekly_fig), style={'flex': '1', 'padding': '10px'}),
        html.Div(dcc.Graph(figure=monthly_fig), style={'flex': '1', 'padding': '10px'})
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-around'})
    
    # Build correlation heat maps.
    # 1 Month correlation heat map.
    one_month_df = pd.DataFrame({sector: series for sector, series in one_month_close.items() if not series.empty})
    if not one_month_df.empty:
        one_month_corr = one_month_df.corr()
        one_month_heatmap = go.Figure(data=go.Heatmap(
            z=one_month_corr.values,
            x=one_month_corr.columns,
            y=one_month_corr.index,
            colorscale='RdBu',
            zmin=-1, zmax=1,
            text=one_month_corr.round(2).values,
            texttemplate="%{text:.2f}",
            colorbar=dict(title="Corr")
        ))
        one_month_heatmap.update_layout(
            title="1 Month Price Correlation",
            xaxis_title="Sector",
            yaxis_title="Sector",
            template="plotly_white",
            margin=dict(t=50, b=50, l=50, r=50)
        )
    else:
        one_month_heatmap = go.Figure()
    
    # 1 Year correlation heat map.
    one_year_df = pd.DataFrame({sector: series for sector, series in one_year_close.items() if not series.empty})
    if not one_year_df.empty:
        one_year_corr = one_year_df.corr()
        one_year_heatmap = go.Figure(data=go.Heatmap(
            z=one_year_corr.values,
            x=one_year_corr.columns,
            y=one_year_corr.index,
            colorscale='RdBu',
            zmin=-1, zmax=1,
            text=one_year_corr.round(2).values,
            texttemplate="%{text:.2f}",
            colorbar=dict(title="Corr")
        ))
        one_year_heatmap.update_layout(
            title="1 Year Price Correlation",
            xaxis_title="Sector",
            yaxis_title="Sector",
            template="plotly_white",
            margin=dict(t=50, b=50, l=50, r=50)
        )
    else:
        one_year_heatmap = go.Figure()
    
    # Arrange the two correlation heat maps side by side.
    heatmaps_layout = html.Div([
        html.Div(dcc.Graph(figure=one_month_heatmap), style={'flex': '1', 'padding': '10px'}),
        html.Div(dcc.Graph(figure=one_year_heatmap), style={'flex': '1', 'padding': '10px'})
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-around'})
    
    # Prepare extended summary table data.
    summary_data = []
    for sector, etf in sectors_etfs.items():
        summary_data.append({
            "Sector": sector,
            "Ticker": etf,
            "Daily (%)": f"{daily_perf.get(sector, 0):.2f}%",
            "Weekly (%)": f"{weekly_perf.get(sector, 0):.2f}%",
            "Monthly (%)": f"{monthly_perf.get(sector, 0):.2f}%",
            "1Q Return (%)": f"{quarter_return.get(sector, 0):.2f}%",
            "Yearly Return (%)": f"{yearly_return.get(sector, 0):.2f}%",
            "Week Range (%)": f"{week_range.get(sector, 0):.2f}%",
            "Month Range (%)": f"{month_range.get(sector, 0):.2f}%",
            "Year Range (%)": f"{year_range.get(sector, 0):.2f}%"
        })
    
    # Create a styled DataTable for the extended summary.
    summary_table = dash_table.DataTable(
        id='summary-table',
        columns=[
            {'name': 'Sector', 'id': 'Sector'},
            {'name': 'Ticker', 'id': 'Ticker'},
            {'name': 'Daily (%)', 'id': 'Daily (%)'},
            {'name': 'Weekly (%)', 'id': 'Weekly (%)'},
            {'name': 'Monthly (%)', 'id': 'Monthly (%)'},
            {'name': '1Q Return (%)', 'id': '1Q Return (%)'},
            {'name': 'Yearly Return (%)', 'id': 'Yearly Return (%)'},
            {'name': 'Week Range (%)', 'id': 'Week Range (%)'},
            {'name': 'Month Range (%)', 'id': 'Month Range (%)'},
            {'name': 'Year Range (%)', 'id': 'Year Range (%)'}
        ],
        data=summary_data,
        sort_action="native",  # Enable sorting
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '14px',
            'color': '#333',
            'border': '1px solid #ddd'
        },
        style_header={
            'backgroundColor': '#2c3e50',
            'fontWeight': 'bold',
            'color': 'white',
            'border': '1px solid #ddd'
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
        ],
        style_table={'width': '90%', 'margin': '20px auto'},
        page_action='none'
    )
    
    # Combine the layouts: performance graphs, correlation heat maps, and summary table.
    full_layout = html.Div([
        graphs_layout,
        html.Br(),
        heatmaps_layout,
        html.Br(),
        summary_table
    ])
    
    print("Performance graphs, correlation heat maps, and extended summary table built successfully.")
    return full_layout

# ------------------------------------
# Run the server
# ------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
