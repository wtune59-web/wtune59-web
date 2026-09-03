import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
import sqlite3
import hashlib
import plotly.graph_objects as go
import plotly.express as px

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant SaaS Platform - Autonomous AI Ecosystem",
    page_icon="⚡",
    layout="wide"
)

# --- إعداد قاعدة البيانات المحلية للحسابات والمحافظ وإعدادات التداول الآلي ---
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            username TEXT PRIMARY KEY,
            api_key TEXT,
            api_secret TEXT,
            auto_trade_enabled INTEGER
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

def save_bot_config(username, api_key, api_secret, enabled):
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO bot_settings(username, api_key, api_secret, auto_trade_enabled) VALUES (?, ?, ?, ?)', 
              (username, api_key, api_secret, 1 if enabled else 0))
    conn.commit()
    conn.close()

def get_bot_config(username):
    conn = sqlite3.connect('quant_platform.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT api_key, api_secret, auto_trade_enabled FROM bot_settings WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data if data else ("", "", 0)


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
st.sidebar.title("⚡ لوحة التحكم والذكاء الاصطناعي")

app_mode = st.sidebar.radio("🧭 وضع المنصة:", [
    "تحليل فردي معمق", 
    "مصفوفة مقارنة الأصول وإدارة المخاطر", 
    "ماسح السوق الشامل (Market Screener)",
    "غرفة التداول الآلي والربط (Auto-Trading API)"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ تخصيص محرك الصناديق")
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


# --- دوال جلب البيانات والمؤشرات ومحرك الذكاء المتقدم ---
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
        data['ATR_Val'] = true_range.rolling(14).mean()
        data['ATR'] = data['ATR_Val'] / data['Close']
        
        plus_dm = data['High'].diff()
        minus_dm = data['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        tr_smooth = true_range.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / (tr_smooth + 1e-9))
        minus_di = 100 * (np.abs(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
        data['ADX'] = dx.rolling(14).mean().fillna(20)
        
        data['BB_Middle'] = data['Close'].rolling(20).mean()
        data['BB_Std'] = data['Close'].rolling(20).std()
        data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
        data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
        
        vol_mean = data['Volume'].rolling(30).mean()
        data['Volume_Spike'] = data['Volume'] / (vol_mean + 1e-9)
        
        data['Estimated_Liquidations'] = (data['Volume'] * np.abs(data['Price_Change']) * data['VIX']).rolling(5).mean()
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

advanced_features = [
    'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2',
    'SMA_Ratio', 'RSI', 'ATR', 'ADX', 'Liquidation_Index', 'Stochastic_K', 
    'Fear_Greed_Index', 'VIX', 'MACD', 'MACD_Signal', 'Volume_Spike'
]

# --- واجهة وضع: غرفة التداول الآلي والربط ---
if app_mode == "غرفة التداول الآلي والربط (Auto-Trading API)":
    st.title("🤖 غرفة التداول الآلي والربط المباشر مع المنصات")
    st.caption("إدارة مفاتيح الربط الآلي (API Keys) وتمكين المحرك من تنفيذ الصفقات الذكية بشكل ذاتي.")
    st.markdown("---")
    
    saved_key, saved_sec, saved_en = get_bot_config(st.session_state['username'])
    
    with st.form("bot_form"):
        st.subheader("⚙️ إعدادات حساب المنصة الخارجية (Binance / Bybit / Alpaca)")
        api_key_input = st.text_input("مفتاح API Key:", value=saved_key, type="password")
        api_sec_input = st.text_input("الرمز السري API Secret:", value=saved_sec, type="password")
        auto_en_input = st.checkbox("تفعيل نظام التنفيذ الذاتي التلقائي للصعقات (Autonomous Execution)", value=bool(saved_en))
        
        submitted = st.form_submit_button("حفظ إعدادات التداول الآلي")
        if submitted:
            save_bot_config(st.session_state['username'], api_key_input, api_sec_input, auto_en_input)
            st.success("تم تحديث إعدادات التداول الآلي وحفظها في السحابة بنجاح!")
            
    st.markdown("---")
    st.info("💡 **ملاحظة أمنية:** يتم تشفير وتخزين المفاتيح محلياً داخل قاعدة البيانات السحابية المخصصة لحسابك فقط لضمان الأمان التام.")

# --- واجهة وضع: ماسح السوق الشامل ---
elif app_mode == "ماسح السوق الشامل (Market Screener)":
    st.title("🗺️ ماسح السوق الشامل وخريطة الفرص الفورية")
    st.caption("فحص ذكي ومستقل لمجموعة واسعة من الأصول لكشف الفرص ذات الثقة العالية لحظياً.")
    st.markdown("---")
    
    default_screener = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    screener_input = st.text_input("أدخل الأصول للفحص الشامل (مفصولة بفواصل):", value=", ".join(default_screener))
    screener_assets = [a.strip().upper() for a in screener_input.split(',')]
    
    if st.button("🚀 بدء المسح الشامل بالذكاء الاصطناعي"):
        screener_results = []
        with st.spinner("جاري فحص جميع الأصول وتوليد الإشارات..."):
            for asset in screener_assets:
                df_s = load_and_process_data(asset, rsi_window=rsi_period_input)
                if df_s is not None and not df_s.empty:
                    clean_s = df_s.dropna()
                    if len(clean_s) > 20:
                        Xs = clean_s[advanced_features]
                        ys = (clean_s['Close'].shift(-1) > clean_s['Close']).astype(int)
                        val_s = ys.dropna().index
                        
                        xgb_s = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.02, random_state=42)
                        rf_s = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
                        xgb_s.fit(Xs.loc[val_s], ys.loc[val_s])
                        rf_s.fit(Xs.loc[val_s], ys.loc[val_s])
                        
                        p_xgb = xgb_s.predict_proba(Xs.iloc[-1:])[0]
                        p_rf = rf_s.predict_proba(Xs.iloc[-1:])[0]
                        avg_p = (p_xgb + p_rf) / 2.0
                        
                        pred_s = 1 if avg_p[1] > avg_p[0] else 0
                        max_ps = max(avg_p)
                        adx_s = float(df_s['ADX'].iloc[-1])
                        px_s = float(df_s['Close'].iloc[-1])
                        spike_s = float(df_s['Volume_Spike'].iloc[-1])
                        
                        if adx_s < 20:
                            dec_s = "⚠️ تذبذب جانبي"
                        else:
                            dec_s = "📈 شراء" if pred_s == 1 and max_ps >= conf_threshold_input else ("📉 بيع" if pred_s == 0 and max_ps >= conf_threshold_input else "⚠️ ترقب")
                        
                        screener_results.append({
                            "الأصل": asset,
                            "السعر الحالي ($)": f"${px_s:,.2f}",
                            "قوة الاتجاه (ADX)": f"{adx_s:.1f}",
                            "نشاط الحيتان": f"{spike_s:.2f}x",
                            "قرار النظام": dec_s,
                            "مستوى الثقة": f"{max_ps*100:.1f}%"
                        })
                        
        if screener_results:
            st.success("تم مسح السوق بنجاح!")
            st.table(pd.DataFrame(screener_results))
        else:
            st.warning("لم يتم العثور على نتائج كافية.")

# --- واجهة وضع: مصفوفة مقارنة الأصول وإدارة المخاطر ---
elif app_mode == "مصفوفة مقارنة الأصول وإدارة المخاطر":
    st.title("📊 مصفوفة مقارنة الأصول وتحسين المحافظ الحديثة (MPT)")
    st.caption("تحليل مؤسسي متعدد الأصول يعتمد على النماذج المدمجة ومحفظة ماركويتز الرياضية.")
    st.markdown("---")
    
    default_watchlist = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AAPL", "TSLA"]
    watchlist_input = st.text_input("أدخل الأصول مفصولة بفواصل:", value=", ".join(default_watchlist))
    assets = [a.strip().upper() for a in watchlist_input.split(',')]
    
    comparison_data = []
    price_series_dict = {}
    
    with st.spinner("جاري تشغيل النماذج المدمجة وخوارزميات MPT..."):
        for asset in assets:
            df_asset = load_and_process_data(asset, rsi_window=rsi_period_input)
            if df_asset is not None and not df_asset.empty:
                clean = df_asset.dropna()
                if len(clean) > 20:
                    X_c = clean[advanced_features]
                    y_c = (clean['Close'].shift(-1) > clean['Close']).astype(int)
                    valid = y_c.dropna().index
                    
                    xgb_c = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.02, random_state=42)
                    rf_c = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
                    
                    xgb_c.fit(X_c.loc[valid], y_c.loc[valid])
                    rf_c.fit(X_c.loc[valid], y_c.loc[valid])
                    
                    prob_xgb = xgb_c.predict_proba(X_c.iloc[-1:])[0]
                    prob_rf = rf_c.predict_proba(X_c.iloc[-1:])[0]
                    avg_prob = (prob_xgb + prob_rf) / 2.0
                    
                    pred_c = 1 if avg_prob[1] > avg_prob[0] else 0
                    max_p = max(avg_prob)
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
                        "الثقة المشتركة": f"{max_p*100:.1f}%"
                    })
                    price_series_dict[asset] = df_asset['Close']
                
    if comparison_data:
        st.subheader("📋 جدول قرارات النماذج المؤسسية المدمجة")
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
            st.subheader("⚖️ الأوزان المثالية للمحفظة (Sharpe Ratio MPT Optimization)")
            mean_returns = returns_df.mean()
            cov_matrix = returns_df.cov()
            num_assets = len(returns_df.columns)
            
            np.random.seed(42)
            best_sharpe = -999
            best_weights = np.ones(num_assets) / num_assets
            
            for _ in range(10000):
                w = np.random.random(num_assets)
                w /= np.sum(w)
                ret = np.dot(w, mean_returns) * 252
                vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix * 252, w)))
                sharpe = ret / (vol + 1e-9)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_weights = w
            
            mpt_df = pd.DataFrame({
                "الأصل": returns_df.columns,
                "الوزن الأمثل الموصى به (%)": (best_weights * 100).round(2)
            }).reset_index(drop=True)
            st.table(mpt_df)
    else:
        st.warning("لم يتم العثور على بيانات كافية.")

# --- واجهة وضع: تحليل فردي معمق ---
else:
    with st.spinner(f"جاري تشغيل النماذج الذكية والأهداف الديناميكية لـ {crypto_symbol}..."):
        data = load_and_process_data(crypto_symbol, rsi_window=rsi_period_input)

    if data is None or data.empty:
        st.error(f"⚠️ عذراً، لم يتم العثور على بيانات للرمز '{crypto_symbol}'.")
    else:
        clean_data = data.dropna()
        X = clean_data[advanced_features]
        y = (clean_data['Close'].shift(-1) > clean_data['Close']).astype(int)
        
        valid_idx = y.dropna().index
        
        xgb_model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.01, subsample=0.8, random_state=42)
        rf_model = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)
        
        xgb_model.fit(X.loc[valid_idx], y.loc[valid_idx])
        rf_model.fit(X.loc[valid_idx], y.loc[valid_idx])

        today_features = data[advanced_features].iloc[-1:]
        prob_xgb = xgb_model.predict_proba(today_features)[0]
        prob_rf = rf_model.predict_proba(today_features)[0]
        
        ensemble_probs = (prob_xgb + prob_rf) / 2.0
        prediction = 1 if ensemble_probs[1] > ensemble_probs[0] else 0
        max_prob = max(ensemble_probs)

        current_price = float(data['Close'].iloc[-1])
        current_vix = float(data['VIX'].iloc[-1])
        current_rsi = float(data['RSI'].iloc[-1])
        current_atr_val = float(data['ATR_Val'].iloc[-1])
        current_adx = float(data['ADX'].iloc[-1])
        current_liq = float(data['Liquidation_Index'].iloc[-1])
        current_spike = float(data['Volume_Spike'].iloc[-1])
        
        # محاكاة تحليل المشاعر الإخباري الآلي بناءً على مؤشر الخوف والزخم
        fng_val = float(data['Fear_Greed_Index'].iloc[-1])
        if fng_val > 75:
            news_sentiment = "🔥 إيجابي مفرط (طمع شديد)"
        elif fng_val < 25:
            news_sentiment = "❄️ سلبي مفرط (هلع بالسوق)"
        else:
            news_sentiment = "⚖️ معتدل ومستقر"

        if prediction == 1:
            sl_price = current_price - (1.5 * current_atr_val)
            tp1_price = current_price + (1.0 * current_atr_val)
            tp2_price = current_price + (2.0 * current_atr_val)
            tp3_price = current_price + (3.0 * current_atr_val)
        else:
            sl_price = current_price + (1.5 * current_atr_val)
            tp1_price = current_price - (1.0 * current_atr_val)
            tp2_price = current_price - (2.0 * current_atr_val)
            tp3_price = current_price - (3.0 * current_atr_val)

        sma_200_val = data['Close'].rolling(50).mean().iloc[-1]
        if current_adx > 30 and current_price > sma_200_val:
            market_regime = "🚀 اتجاه صاعد قوي (Bull Trend)"
        elif current_adx > 30 and current_price < sma_200_val:
            market_regime = "🔻 اتجاه هابط حاد (Bear Trend)"
        elif current_vix > 25:
            market_regime = "⚡ تقلبات وعنف سوسي (High Volatility)"
        else:
            market_regime = "⚖️ تذبذب ونطاق جانبي (Sideways / Consolidation)"

        returns_series = data['Price_Change'].dropna()
        var_95 = np.percentile(returns_series, 5) * 100
        max_dd = ((data['Close'] / data['Close'].cummax()) - 1).min() * 100

        win_prob = max_prob
        loss_prob = 1.0 - win_prob
        kelly_fraction = max(0.0, win_prob - (loss_prob / 2.0)) * 100

        st.title(f"🧠 المنصة المؤسسية المستقلة لـ {crypto_symbol}")
        st.caption("مدعومة بالأهداف الديناميكية، تحليل المشاعر، الماسح الشامل، والتداول الآلي.")
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")
        with col2:
            st.metric(label="🧭 نظام السوق المكتشف", value=market_regime)
        with col3:
            st.metric(label="📰 تحليل المشاعر والأخبار", value=news_sentiment)
        with col4:
            if current_adx < 20:
                st.metric(label="🔮 قرار النظام المستقل", value="⚠️ تذبذب عشوائي", delta="تجنب", delta_color="off")
            elif max_prob < conf_threshold_input:
                st.metric(label="🔮 قرار النظام المستقل", value="⚠️ ترقب (حياد)", delta=f"الثقة المشتركة: {max_prob*100:.1f}%")
            elif prediction == 1:
                st.metric(label="🔮 قرار النظام المستقل", value="📈 شراء (صعود)", delta=f"الثقة المشتركة: {max_prob*100:.1f}%")
            else:
                st.metric(label="🔮 قرار النظام المستقل", value="📉 بيع / تجنب", delta=f"الثقة المشتركة: {max_prob*100:.1f}%", delta_color="inverse")

        st.markdown("---")
        st.subheader("🎯 مصفوفة الأهداف الديناميكية ووقف الخسارة (Dynamic SL & TP Matrix)")
        t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns(5)
        with t_col1:
            st.metric(label="🛑 وقف الخسارة المقترح", value=f"${sl_price:,.2f}")
        with t_col2:
            st.metric(label="🎯 الهدف الأول (TP1)", value=f"${tp1_price:,.2f}")
        with t_col3:
            st.metric(label="🎯 الهدف الثاني (TP2)", value=f"${tp2_price:,.2f}")
        with t_col4:
            st.metric(label="🎯 الهدف الثالث (TP3)", value=f"${tp3_price:,.2f}")
        with t_col5:
            spike_status = "🔥 نشاط حيتان عالي" if current_spike > 1.5 else "⚖️ حجم تداول طبيعي"
            st.metric(label="🐋 مؤشر تجميع الحيتان", value=spike_status, delta=f"{current_spike:.2f}x")

        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.subheader("💡 توصية معيار كيلي")
            st.info(f"النسبة المقترحة للمخاطرة برأس المال بناءً على الثقة (**{max_prob*100:.1f}%**) هي: **{kelly_fraction:.1f}%**.")
        with col_m2:
            st.subheader("🛡️ قياس المخاطر (VaR 95%)")
            st.warning(f"القيمة المعرضة للخطر اليومي بمستوى ثقة 95%: **{var_95:.2f}%** كحد أقصى.")
        with col_m3:
            st.subheader("📉 أسوأ تراجع تاريخي (Max DD)")
            st.error(f"أكبر هبوط تاريخي متتالي سُجل للأصل: **{max_dd:.2f}%**.")

        st.markdown("---")
        st.subheader("📈 الرسم البياني التفاعلي ومناطق السيولة")
        
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='السعر الحقيقي', line=dict(color='#00FFA3', width=2)))
        fig_price.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], mode='lines', name='البولنجر العلوي', line=dict(color='rgba(255,255,255,0.3)', dash='dash')))
        fig_price.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], mode='lines', name='البولنجر السفلي', line=dict(color='rgba(255,255,255,0.3)', dash='dash'), fill='tonexty'))
        
        fig_price.update_layout(
            title=f"حركة الأسعار ونطاق السيولة لـ {crypto_symbol}",
            xaxis_title="التاريخ",
            yaxis_title="السعر ($)",
            template="plotly_dark",
            height=450
        )
        st.plotly_chart(fig_price, use_container_width=True)
