import streamlit as st
from datetime import datetime, timedelta
import yfinance as yf
import plotly.graph_objects as go
import ta
if "data_cache" not in st.session_state:
    st.session_state["data_cache"] = {}
if "recent_stocks" not in st.session_state:
    st.session_state["recent_stocks"] = []
if "current_stock" not in st.session_state:
    st.session_state["current_stock"] = ""
st.set_page_config(page_title="📈 Stock Analysis Dashboard", layout="wide")
st.title("📈 Stock Analysis Dashboard")
st.markdown("---")
with st.sidebar:
    st.header("🔍 Stock Input")
    user_input = st.text_input("Stock Symbol (e.g., AAPL, TSLA):", value=st.session_state.current_stock)
    if user_input and user_input != st.session_state.current_stock:
        st.session_state.current_stock = user_input.upper()
    st.markdown("---")
    st.subheader("📊 Technical Indicators")
    show_rsi = st.checkbox("RSI (14 days)", value=True)
    show_sma = st.checkbox("SMA (50 days)", value=True)
    show_ema = st.checkbox("EMA (20 days)")
    show_macd = st.checkbox("MACD")
    st.markdown("---")
    st.subheader("🕘 Recent Stocks")
    for stock in st.session_state["recent_stocks"]:
        if st.button(stock, key=f"recent_{stock}"):
            st.session_state.current_stock = stock
    if st.button("Clear Recent"):
        st.session_state["recent_stocks"] = []
    if st.button("Clear Cache"):
        st.session_state["data_cache"] = {}
        st.success("Cache cleared!")
@st.cache_data(show_spinner=False)
def fetch_stock_data(symbol, start, end):
    key = f"{symbol}_{start.date()}_{end.date()}"
    if key in st.session_state["data_cache"]:
        return st.session_state["data_cache"][key]
    df = yf.Ticker(symbol).history(start=start, end=end)
    st.session_state["data_cache"][key] = df
    return df
def add_indicators(df, rsi=False, sma=False, ema=False, macd=False):
    if df.empty:
        return df
    if rsi:
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    if sma:
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
    if ema:
        df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    if macd:
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    return df
if st.session_state.current_stock:
    symbol = st.session_state.current_stock
    start_date = datetime.now() - timedelta(days=365 * 5)
    end_date = datetime.now()
    raw_df = fetch_stock_data(symbol, start_date, end_date)
    df = add_indicators(raw_df.copy(), rsi=show_rsi, sma=show_sma, ema=show_ema, macd=show_macd)
    if df.empty:
        st.error(f"No data found for {symbol}. Check the symbol.")
    else:
        if symbol not in st.session_state["recent_stocks"]:
            st.session_state["recent_stocks"].insert(0, symbol)
            st.session_state["recent_stocks"] = st.session_state["recent_stocks"][:5]
        st.subheader(f"📊 {symbol} | Last 5 Years")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Price"))
        if show_sma and "SMA_50" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA 50", line=dict(color="blue", width=1.5)))
        if show_ema and "EMA_20" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_20"], name="EMA 20", line=dict(color="orange", width=1.5)))
        if show_macd and "MACD" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="green", width=1)))
            fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal Line", line=dict(color="red", width=1)))
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="rgba(0, 102, 204, 0.3)", yaxis='y2'))
        if show_rsi and "RSI" in df:
            fig.add_trace(go.Scatter(x=df.index, y=[70]*len(df), name="Overbought", line=dict(color="red", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=df.index, y=[30]*len(df), name="Oversold", line=dict(color="green", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="purple", width=2), yaxis='y3'))
        fig.update_layout(
            title=f"{symbol} Technical Analysis",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
            yaxis3=dict(title="RSI", overlaying="y", side="right", anchor="free", position=1, showgrid=False, range=[0, 100]) if show_rsi else {},
            height=700,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        tab1, tab2 = st.tabs(["📈 Interactive Chart", "📋 Data Summary"])
        with tab1:
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            left, right = st.columns(2)
            with left:
                st.subheader("📊 Key Metrics")
                latest_close = df["Close"].iloc[-1]
                prev_close = df["Close"].iloc[-2] if len(df) > 1 else latest_close
                change = latest_close - prev_close
                pct_change = (change / prev_close) * 100 if prev_close else 0
                c1, c2, c3 = st.columns(3)
                c1.metric("💲 Current Price", f"${latest_close:.2f}")
                c2.metric("📈 Daily Change", f"${change:.2f}")
                c3.metric("📊 Daily % Change", f"{pct_change:.2f}%")
                st.markdown("---")
                if show_rsi and "RSI" in df:
                    current_rsi = df["RSI"].iloc[-1]
                    rsi_status = "Overbought" if current_rsi > 70 else "Oversold" if current_rsi < 30 else "Neutral"
                    st.metric("📉 Current RSI", f"{current_rsi:.2f}", rsi_status)
                if show_macd and "MACD" in df and "Signal" in df:
                    macd_diff = df["MACD"].iloc[-1] - df["Signal"].iloc[-1]
                    macd_status = "Bullish" if macd_diff > 0 else "Bearish"
                    st.metric("📊 MACD Status", macd_status)
            with right:
                st.subheader("📅 Historical Extremes")
                lowest_volume = df["Volume"].idxmin()
                highest_volume = df["Volume"].idxmax()
                lowest_close = df["Close"].idxmin()
                highest_close = df["Close"].idxmax()
                avg_volume = df["Volume"].mean()
                v1, v2 = st.columns(2)
                v1.metric("📉 Lowest Volume", f"{df.loc[lowest_volume]['Volume']:,}")
                v2.metric("📈 Highest Volume", f"{df.loc[highest_volume]['Volume']:,}")
                p1, p2 = st.columns(2)
                p1.metric("🔻 Lowest Close", f"${df.loc[lowest_close]['Close']:.2f}")
                p2.metric("🔺 Highest Close", f"${df.loc[highest_close]['Close']:.2f}")
                st.markdown("---")
                st.metric("📊 Avg Daily Volume", f"{avg_volume:,.0f}")
                try:
                    market_cap = yf.Ticker(symbol).info.get("marketCap", "N/A")
                    market_cap = f"${market_cap/1e9:.2f} B" if isinstance(market_cap, (int, float)) else "N/A"
                except:
                    market_cap = "N/A"
                st.metric("🏢 Market Cap", market_cap)
st.markdown("---")
st.markdown("ℹ️ Data from Yahoo Finance | Made with Streamlit")
