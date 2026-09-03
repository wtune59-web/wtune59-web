import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier
import xml.etree.ElementTree as ET
import sqlite3
import hashlib
import plotly.graph_objects as go
import plotly.express as px

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant SaaS Platform - Liquidations & Liquidity Edition",
    page_icon="⚡",
    layout="wide"
)

# --- إعداد قاعدة البيانات المحلية للحسابات والمحافظ ---
def init_db():
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            username TEXT,
            symbol TEXT,
            qty REAL,
            buy_price REAL,
            PRIMARY KEY (username, symbol)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(username, password):
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data and data[0] == make_hash(password):
        return True
    return False

def add_user(username, password):
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?, ?)', (username, make_hash(password)))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def save_user_portfolio(username, symbol, qty, buy_price):
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO portfolios(username, symbol, qty, buy_price) VALUES (?, ?, ?, ?)', 
              (username, symbol, qty, buy_price))
    conn.commit()
    conn.close()

def get_user_portfolio(username, symbol):
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT qty, buy_price FROM portfolios WHERE username = ? AND symbol = ?', (username, symbol))
    data = c.fetchone()
    conn.close()
    return data if data else (0.0, 0.0)


# --- نظام إدارة تسجيل الدخول في الشريط الجانبي ---
st.sidebar.title("🔐 بوابة المستخدمين السحابية")
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""

if not st.session_state['logged_in']:
    auth_mode = st.sidebar.radio("اختر العملية:", ["تسجيل الدخول", "إنشاء حساب جديد"])
    u_input = st.sidebar.text_input("اسم المستخدم:")
    p_input = st.sidebar.text_input("كلمة المرور:", type="password")
    
    if auth_mode == "تسجيل الدخول":
        if st.sidebar.button("دخول للمنصة"):
            if check_user(u_input, p_input):
                st.session_state['logged_in'] = True
                st.session_state['username'] = u_input
                st.rerun()
            else:
                st.sidebar.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
    else:
        if st.sidebar.button("تسجيل الحساب"):
            if add_user(u_input, p_input):
                st.sidebar.success("تم إنشاء الحساب بنجاح! يمكنك تسجيل الدخول الآن.")
            else:
                st.sidebar.error("اسم المستخدم مستخدم مسبقاً.")
    st.stop()

st.sidebar.success(f"مرحباً بك، {st.session_state['username']} 👋")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("⚡ لوحة التحكم والسيولة")

app_mode = st.sidebar.radio("🧭 وضع المنصة:", ["تحليل فردي معمق", "مصفوفة مقارنة الأصول وإدارة المخاطر"])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ تخصيص محرك الذكاء الاصطناعي")
conf_threshold_input = st.sidebar.slider("عتبة الثقة المطلوبة (Confidence %):", min_value=50, max_value=85, value=60, step=5) / 100.0
rsi_period_input = st.sidebar.slider("فترة مؤشر الزخم (RSI Period):", min_value=7, max_value=28, value=14, step=1)

crypto_symbol = "BTC-USD"
if app_mode == "تحليل فردي معمق":
    user_symbol_input = st.sidebar.text_input("🔍 أدخل رمز الأصل:", value="BTC-USD")
    crypto_symbol = user_symbol_input.strip().upper()
    
    saved_qty, saved_buy = get_user_portfolio(st.session_state['username'], crypto_symbol)
    st.sidebar.markdown("---")
    st.sidebar.header("💼 إدارة محفظتك السحابية")
    portfolio_qty = st.sidebar.number_input("الكمية المملوكة:", min_value=0.0, value=float(saved_qty), step=0.01)
    portfolio_buy_price = st.sidebar.number_input("متوسط سعر الشراء ($):", min_value=0.0, value=float(saved_buy), step=100.0)
    
    if st.sidebar.button("💾 حفظ تعديلات المحفظة"):
        save_user_portfolio(st.session_state['username'], crypto_symbol, portfolio_qty, portfolio_buy_price)
        st.sidebar.success("تم حفظ محفظتك في السحابة بنجاح!")


# --- دوال جلب البيانات والمؤشرات وتصفيات السوق ---
@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        url = "https://api.alternative.me/fng/?limit=0"
        response = requests.get(url).json()
        df = pd.DataFrame(response['data'])
        df['value'] = df['value'].astype(int)
        df['Date'] = pd.to_datetime(df['timestamp'].astype(int), unit='s').dt.strftime('%Y-%m-%d')
        return df[['Date', 'value']].rename(columns={'value': 'Fear_Greed_Index'})
    except:
        return None

@st.cache_data(ttl=3600)
def get_vix_data():
    try:
        vix = yf.download('^VIX', period='1y', progress=False)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        vix = vix.reset_index()
        vix['Date'] = pd.to_datetime(vix['Date']).dt.strftime('%Y-%m-%d')
        return vix[['Date', 'Close']].rename(columns={'Close': 'VIX'})
    except:
        return None

@st.cache_data(ttl=3600)
def load_and_process_data(symbol, rsi_window=14):
    try:
        data = yf.download(symbol, period='1y', progress=False)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        data = data.reset_index()
        data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
        
        fng_df = get_fear_and_greed()
        if fng_df is not None:
            data = pd.merge(data, fng_df, on='Date', how='left')
            data['Fear_Greed_Index'] = data['Fear_Greed_Index'].fillna(50)
        else:
            data['Fear_Greed_Index'] = 50

        vix_df = get_vix_data()
        if vix_df is not None:
            data = pd.merge(data, vix_df, on='Date', how='left')
            data['VIX'] = data['VIX'].fillna(20.0)
        else:
            data['VIX'] = 20.0
            
        data.set_index('Date', inplace=True)
        
        data['Price_Change'] = data['Close'].pct_change()
        data['Volume_Change'] = data['Volume'].pct_change()
        data['Lag_1'] = data['Price_Change'].shift(1)
        data['Lag_2'] = data['Price_Change'].shift(2)
        
        data['SMA_10'] = data['Close'].rolling(10).mean()
        data['SMA_30'] = data['Close'].rolling(30).mean()
        data['SMA_Ratio'] = data['SMA_10'] / data['SMA_30']
        
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(rsi_window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_window).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        data['ATR'] = true_range.rolling(14).mean() / data['Close']
        
        plus_dm = data['High'].diff()
        minus_dm = data['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        tr_smooth = true_range.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / (tr_smooth + 1e-9))
        minus_di = 100 * (np.abs(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
        data['ADX'] = dx.rolling(14).mean().fillna(20)
        
        # محرك تقدير وتصفيات السيولة (Estimated Liquidation Index)
        # يعتمد على التغير المفاجئ في الحجم مقارنة بالمدى السعري لضرب عقود الرافعة المالية
        data['Estimated_Liquidations'] = (data['Volume'] * np.abs(data['Price_Change']) * data['VIX']).rolling(5).mean()
        # تطبيع مؤشر التصفيات ليكون بين 0 و 100
        liq_min = data['Estimated_Liquidations'].min()
        liq_max = data['Estimated_Liquidations'].max()
        data['Liquidation_Index'] = 100 * (data['Estimated_Liquidations'] - liq_min) / (liq_max - liq_min + 1e-9)
        data['Liquidation_Index'] = data['Liquidation_Index'].fillna(50)
        
        low_14 = data['Low'].rolling(14).min()
        high_14 = data['High'].rolling(14).max()
        data['Stochastic_K'] = 100 * (data['Close'] - low_14) / (high_14 - low_14 + 1e-9)
        
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        
        return data
    except:
        return None

@st.cache_data(ttl=3600)
def get_news_sentiment(symbol):
    try:
        ticker_base = symbol.split('-')[0]
        rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker_base}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(rss_url, headers=headers, timeout=3)
        
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            titles = [elem.text for elem in root.iter('title') if elem.text]
            positive_words = ['surge', 'jump', 'gain', 'bull', 'rally', 'high', 'growth', 'up']
            negative_words = ['drop', 'fall', 'crash', 'bear', 'loss', 'down', 'risk']
            
            score = 0
            for title in titles[:5]:
                t_lower = title.lower()
                for p in positive_words:
                    if p in t_lower: score += 1
                for n in negative_words:
                    if n in t_lower: score -= 1
                
            if score > 0: return "إيجابي 🟢", titles[:3]
            elif score < 0: return "سلبي 🔴", titles[:3]
        return "محايد ⚪", ["لا توجد أخبار بارزة حديثة."]
    except:
        return "محايد ⚪", ["تعذر جلب الأخبار الحية."]


advanced_features = [
    'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2',
    'SMA_Ratio', 'RSI', 'ATR', 'ADX', 'Liquidation_Index', 'Stochastic_K', 
    'Fear_Greed_Index', 'VIX', 'MACD', 'MACD_Signal'
]

if app_mode == "مصفوفة مقارنة الأصول وإدارة المخاطر":
    st.title("📊 مصفوفة مقارنة الأصول وسيولة السوق")
    st.caption("تحليل مؤسسي متعدد الأصول مدعوم بمؤشرات تصفية الرافعة المالية والسيولة.")
    st.markdown("---")
    
    default_watchlist = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AAPL", "TSLA"]
    watchlist_input = st.text_input("أدخل الأصول مفصولة بفواصل:", value=", ".join(default_watchlist))
    assets = [a.strip().upper() for a in watchlist_input.split(',')]
    
    comparison_data = []
    price_series_dict = {}
    
    with st.spinner("جاري تشغيل محرك السيولة والارتباط..."):
        for asset in assets:
            df_asset = load_and_process_data(asset, rsi_window=rsi_period_input)
            if df_asset is not None and not df_asset.empty:
                clean = df_asset.dropna()
                if len(clean) > 20:
                    X_c = clean[advanced_features]
                    y_c = (clean['Close'].shift(-1) > clean['Close']).astype(int)
                    valid = y_c.dropna().index
                    
                    model_c = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.02, random_state=42)
                    model_c.fit(X_c.loc[valid], y_c.loc[valid])
                    
                    pred_c = model_c.predict(X_c.iloc[-1:])[0]
                    prob_c = model_c.predict_proba(X_c.iloc[-1:])[0]
                    max_p = max(prob_c)
                    current_adx = float(df_asset['ADX'].iloc[-1])
                    current_liq = float(df_asset['Liquidation_Index'].iloc[-1])
                    
                    if current_adx < 20:
                        decision = "⚠️ تذبذب عشوائي"
                    else:
                        decision = "📈 شراء" if pred_c == 1 and max_p >= conf_threshold_input else ("📉 بيع" if pred_c == 0 and max_p >= conf_threshold_input else "⚠️ ترقب")
                    
                    current_px = float(df_asset['Close'].iloc[-1])
                    
                    comparison_data.append({
                        "الأصل": asset,
                        "السعر الحالي ($)": f"${current_px:,.2f}",
                        "مؤشر التصفيات": f"{current_liq:.1f}/100",
                        "ADX": f"{current_adx:.1f}",
                        "قرار النظام": decision,
                        "نسبة الثقة": f"{max_p*100:.1f}%"
                    })
                    price_series_dict[asset] = df_asset['Close']
                
    if comparison_data:
        st.subheader("📋 جدول القرارات وسيولة الحيتان")
        st.table(pd.DataFrame(comparison_data))
        
        if len(price_series_dict) > 1:
            st.markdown("---")
            st.subheader("🔗 مصفوفة الارتباط بين الأصول (Correlation Matrix)")
            prices_df = pd.DataFrame(price_series_dict).dropna()
            returns_df = prices_df.pct_change().dropna()
            corr_matrix = returns_df.corr()
            
            fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale="RdBu_r", aspect="auto")
            st.plotly_chart(fig_corr, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⚖️ الأوزان المثالية للمحفظة (Inverse Volatility MPT)")
            volatilities = returns_df.std()
            inv_vol = 1.0 / (volatilities + 1e-9)
            weights = inv_vol / inv_vol.sum()
            
            weights_df = pd.DataFrame({
                "الأصل": weights.index,
                "الوزن المقترح بالمحفظة (%)": (weights.values * 100).round(2)
            }).reset_index(drop=True)
            st.table(weights_df)
    else:
        st.warning("لم يتم العثور على بيانات كافية.")

else:
    with st.spinner(f"جاري معالجة التحليل وتحليل السيولة لـ {crypto_symbol}..."):
        data = load_and_process_data(crypto_symbol, rsi_window=rsi_period_input)
        sentiment_label, news_headlines = get_news_sentiment(crypto_symbol)

    if data is None or data.empty:
        st.error(f"⚠️ عذراً، لم يتم العثور على بيانات للرمز '{crypto_symbol}'.")
    else:
        clean_data = data.dropna()
        X = clean_data[advanced_features]
        y = (clean_data['Close'].shift(-1) > clean_data['Close']).astype(int)
        
        valid_idx = y.dropna().index
        model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.01, subsample=0.8, random_state=42)
        model.fit(X.loc[valid_idx], y.loc[valid_idx])

        today_features = data[advanced_features].iloc[-1:]
        prediction = model.predict(today_features)[0]
        probabilities = model.predict_proba(today_features)[0]

        current_price = float(data['Close'].iloc[-1])
        current_fng = int(data['Fear_Greed_Index'].iloc[-1])
        current_vix = float(data['VIX'].iloc[-1])
        current_rsi = float(data['RSI'].iloc[-1])
        current_atr = float(data['ATR'].iloc[-1])
        current_adx = float(data['ADX'].iloc[-1])
        current_liq = float(data['Liquidation_Index'].iloc[-1])
        
        stop_loss_val = current_price * (1 - (current_atr * 1.5))
        take_profit_val = current_price * (1 + (current_atr * 2.5))
        max_prob = max(probabilities)

        st.title(f"🧠 منصة التحليل الاحترافية وسيولة الحيتان لـ {crypto_symbol}")
        st.caption("مدعوم بنماذج XGBoost مع محرك تتبع عمليات تصفية الرافعة المالية (Liquidations).")
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")
        with col2:
            st.metric(label="🌊 ضغط التصفيات والسيولة", value=f"{current_liq:.1f} / 100")
        with col3:
            st.metric(label="📊 قوة الاتجاه (ADX)", value=f"{current_adx:.1f}")
        with col4:
            if current_adx < 20:
                st.metric(label="🔮 قرار النظام", value="⚠️ تذبذب عشوائي", delta="تجنب", delta_color="off")
            elif max_prob < conf_threshold_input:
                st.metric(label="🔮 قرار النظام", value="⚠️ ترقب (حياد)", delta=f"الثقة: {max_prob*100:.1f}%")
            elif prediction == 1:
                st.metric(label="🔮 قرار النظام", value="📈 شراء (صعود)", delta=f"الثقة: {max_prob*100:.1f}%")
            else:
                st.metric(label="🔮 قرار النظام", value="📉 بيع / تجنب", delta=f"الثقة: {max_prob*100:.1f}%", delta_color="inverse")

        st.markdown("---")
        st.subheader("📈 الرسم البياني التفاعلي للسيولة وحركة الأسعار")
        
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='السعر الحقيقي', line=dict(color='#00FFA3', width=2)))
        fig_price.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], mode='lines', name='البولنجر العلوي', line=dict(color='rgba(255,255,255,0.3)', dash='dash')))
        fig_price.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], mode='lines', name='البولنجر السفلي', line=dict(color='rgba(255,255,255,0.3)', dash='dash'), fill='tonexty'))
        
        fig_price.update_layout(
            title=f"حركة الأسعار ومناطق السيولة لـ {crypto_symbol}",
            xaxis_title="التاريخ",
            yaxis_title="السعر ($)",
            template="plotly_dark",
            height=450
        )
        st.plotly_chart(fig_price, use_container_width=True)

        st.markdown("---")
        st.subheader("🧪 محرك الاختبار العكسي التفاعلي (Interactive Backtest)")
        clean_data['Model_Pred'] = model.predict(X)
        clean_data['Strategy_Return'] = clean_data['Model_Pred'].shift(1) * clean_data['Price_Change']
        strategy_cum = (1 + clean_data['Strategy_Return'].fillna(0)).cumprod() - 1
        buyhold_cum = (1 + clean_data['Price_Change']).cumprod() - 1
        
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=clean_data.index, y=strategy_cum * 100, mode='lines', name='استراتيجية الذكاء الاصطناعي (%)', line=dict(color='#FF007F', width=2)))
        fig_bt.add_trace(go.Scatter(x=clean_data.index, y=buyhold_cum * 100, mode='lines', name='الشراء والاحتفاظ التقليدي (%)', line=dict(color='#00E5FF', width=2)))
        
        fig_bt.update_layout(
            title="مقارنة الأداء التاريخي للاستراتيجية مقابل السوق",
            xaxis_title="التاريخ",
            yaxis_title="العائد النسبة المئوية (%)",
            template="plotly_dark",
            height=400
        )
        st.plotly_chart(fig_bt, use_container_width=True)
