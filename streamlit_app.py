import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import MinMaxScaler
import sqlite3
import hashlib
import plotly.graph_objects as go
import plotly.express as px
import datetime
import uuid

# محاولة استيراد XGBoost
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# محاولة استيراد TensorFlow لشبكات LSTM العميقة
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant SaaS Platform - Apex Titan Pro Max 2026 Institutional",
    page_icon="⚡",
    layout="wide"
)

# --- إعداد قاعدة البيانات الشاملة ---
DB_NAME = 'apex_titan_2026_inst.db'

def init_db():
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, api_token TEXT, score REAL DEFAULT 100.0, is_trader INTEGER DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS portfolios (username TEXT, symbol TEXT, qty REAL, buy_price REAL, PRIMARY KEY (username, symbol))')
        c.execute('CREATE TABLE IF NOT EXISTS trade_journal (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, symbol TEXT, action TEXT, price REAL, qty REAL, date TEXT, pnl REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS social_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, date TEXT, win_rate REAL DEFAULT 0.0)')
        c.execute('CREATE TABLE IF NOT EXISTS copy_trading (follower TEXT, trader TEXT, allocation_pct REAL, PRIMARY KEY (follower, trader))')
        conn.commit()

init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(username, password):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute('SELECT password FROM users WHERE username = ?', (username,))
        data = c.fetchone()
        return data and data[0] == make_hash(password)

def add_user(username, password):
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            c = conn.cursor()
            token = str(uuid.uuid4())
            c.execute('INSERT INTO users(username, password, api_token, score, is_trader) VALUES (?, ?, ?, ?, ?)', (username, make_hash(password), token, 100.0, 1))
            conn.commit()
            return True
    except:
        return False

def log_trade(username, symbol, action, price, qty, pnl=0.0):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO trade_journal(username, symbol, action, price, qty, date, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  (username, symbol, action, price, qty, date_str, pnl))
        c.execute('SELECT follower FROM copy_trading WHERE trader = ?', (username,))
        followers = c.fetchall()
        for f in followers:
            c.execute('INSERT INTO trade_journal(username, symbol, action, price, qty, date, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                      (f[0], f"COPY-{symbol}", f"COPY-{action}", price, qty, date_str, pnl))
        conn.commit()

def get_trade_journal(username):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        return pd.read_sql_query('SELECT id, symbol, action, price, qty, date, pnl FROM trade_journal WHERE username = ?', conn, params=(username,))

# --- دالة جلب قائمة أعلى العملات الرقمية ديناميكياً ---
@st.cache_data(ttl=43200)
def fetch_top_crypto_symbols(limit=250):
    symbols = []
    try:
        pages = (limit // 100) + (1 if limit % 100 != 0 else 0)
        headers = {'User-Agent': 'Mozilla/5.0'}
        for page in range(1, pages + 1):
            url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}"
            res = requests.get(url, headers=headers, timeout=5).json()
            if isinstance(res, list):
                for item in res:
                    symbols.append(f"{item['symbol'].upper()}-USD")
            if len(symbols) >= limit:
                break
    except Exception:
        pass
    
    fallback_list = [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", 
        "AVAX-USD", "SHIB-USD", "DOT-USD", "LINK-USD", "SUI-USD", "NEAR-USD", "LTC-USD", 
        "PEPE-USD", "FET-USD", "RENDER-USD", "TAO-USD", "APT-USD", "ICP-USD", "KAS-USD", 
        "INJ-USD", "XMR-USD", "TRX-USD", "ETC-USD", "BCH-USD", "FIL-USD", "ATOM-USD",
        "ARB-USD", "OP-USD", "MATIC-USD", "STX-USD", "LDO-USD", "TIA-USD", "RUNE-USD",
        "BONK-USD", "FLOKI-USD", "WIF-USD", "SEI-USD", "AAVE-USD", "MKR-USD", "UNI-USD"
    ]
    
    combined = list(dict.fromkeys(symbols + fallback_list))
    return combined[:limit]

# --- نظام تسجيل الدخول والشريط الجانبي ---
st.sidebar.title("🔐 بوابة المؤسسات السحابية (Titan Inst)")
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
                st.sidebar.error("خطأ في بيانات الدخول.")
    else:
        if st.sidebar.button("تسجيل الحساب"):
            if add_user(u_input, p_input):
                st.sidebar.success("تم إنشاء الحساب وتفعيله!")
            else:
                st.sidebar.error("اسم المستخدم مستخدم مسبقاً.")
    st.stop()

st.sidebar.success(f"مرحباً بك، {st.session_state['username']} ⚡")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("🧭 لوحة التحكم المؤسسية")

app_mode = st.sidebar.radio("الوضع التشغيلي:", [
    "تحليل فردي معمق وإدارة الأصول",
    "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)",
    "🧪 محرك الاختبار الخلفي المؤسسي (Institutional Backtesting)",
    "👥 شبكة التداول الاجتماعي ونسخ الصفقات (Copy Trading)",
    "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)",
    "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)",
    "🧪 مختبر تحسين النماذج المتقدم (ML & Deep Learning Lab)",
    "ماسح السوق الشامل (Market Screener)",
    "سجل الصفقات الحي والأداء (Trade Journal & PnL)"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ إعدادات المحرك المؤسسي")
conf_threshold_input = st.sidebar.slider("عتبة الثقة المؤسسية (%):", 50, 85, 60, 5) / 100.0
rsi_period_input = st.sidebar.slider("فترة مؤشر الزخم (RSI):", 7, 28, 14, 1)

algo_options = ["Random Forest", "Gradient Boosting"]
if XGB_AVAILABLE:
    algo_options.append("XGBoost")
if LSTM_AVAILABLE:
    algo_options.append("Deep Learning (LSTM)")
model_algo_choice = st.sidebar.selectbox("خوارزمية الذكاء الاصطناعي:", algo_options)

all_available_cryptos = fetch_top_crypto_symbols(limit=250)

crypto_symbol = "BTC-USD"
if app_mode in ["تحليل فردي معمق وإدارة الأصول", "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)", "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)", "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)"]:
    selected_crypto = st.sidebar.selectbox(f"اختر من العملات المتاحة ({len(all_available_cryptos)} عملة):", all_available_cryptos)
    custom_symbol_input = st.sidebar.text_input("أو ابحث/اكتب رمز أي عملة عالمية مباشرة (مثال: FLOKI أو BONK):", value="")
    
    if custom_symbol_input.strip():
        user_raw = custom_symbol_input.strip().upper()
        crypto_symbol = user_raw if user_raw.endswith("-USD") else f"{user_raw}-USD"
    else:
        crypto_symbol = selected_crypto

# --- دوال جلب البيانات والمعالجة المحسنة ---
@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        url = "https://api.alternative.me/fng/?limit=0"
        response = requests.get(url, timeout=5).json()
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
        if vix is None or vix.empty: return None
        if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
        vix = vix.reset_index()
        vix['Date'] = pd.to_datetime(vix['Date']).dt.strftime('%Y-%m-%d')
        return vix[['Date', 'Close']].rename(columns={'Close': 'VIX'})
    except:
        return None

@st.cache_data(ttl=3600)
def load_and_process_data(symbol, rsi_window=14):
    try:
        data = yf.download(symbol, period='1y', progress=False)
        if data is None or data.empty: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_cols): return None
            
        data = data.reset_index()
        data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
        
        fng_df = get_fear_and_greed()
        data = pd.merge(data, fng_df, on='Date', how='left') if fng_df is not None else data.assign(Fear_Greed_Index=50)
        data['Fear_Greed_Index'] = data['Fear_Greed_Index'].fillna(50)

        vix_df = get_vix_data()
        data = pd.merge(data, vix_df, on='Date', how='left') if vix_df is not None else data.assign(VIX=20.0)
        data['VIX'] = data['VIX'].fillna(20.0)
            
        data.set_index('Date', inplace=True)
        for col in required_cols: data[col] = pd.to_numeric(data[col], errors='coerce')
                
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
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
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
        
        data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
        data = data.bfill().ffill().fillna(0)
        return data
    except Exception:
        return None

advanced_features = ['Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2', 'SMA_Ratio', 'RSI', 'ATR', 'ADX', 'Fear_Greed_Index', 'VIX']

def get_trained_model(algo_name):
    if algo_name == "Gradient Boosting":
        return GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
    elif algo_name == "XGBoost" and XGB_AVAILABLE:
        return xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric='logloss')
    elif algo_name == "Deep Learning (LSTM)" and LSTM_AVAILABLE:
        return None
    else:
        return RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)

# --- واجهات المنصة ---
if app_mode == "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)":
    st.title("🤖 المساعد الذكي للتحليل المدمج")
    user_q = st.text_input("أدخل سؤالك المالي:")
    if st.button("💬 إرسال للمساعد الذكي"):
        df_q = load_and_process_data(crypto_symbol)
        if df_q is not None and not df_q.empty:
            cur_p, cur_rsi = float(df_q['Close'].iloc[-1]), float(df_q['RSI'].iloc[-1])
            st.info(f"التحليل الخاص بـ ({crypto_symbol}):\n- السعر: ${cur_p:,.2f}\n- RSI: {cur_rsi:.1f}")
        else:
            st.error(f"تعذر جلب البيانات للرمز '{crypto_symbol}'.")

elif app_mode == "🧪 محرك الاختبار الخلفي المؤسسي (Institutional Backtesting)":
    st.title("🧪 محرك الاختبار الخلفي")
    bt_symbol = st.selectbox("اختر العملة للاختبار:", all_available_cryptos)
    if st.button("🚀 تشغيل محاكاة الاختبار"):
        df_bt = load_and_process_data(bt_symbol)
        if df_bt is not None and not df_bt.empty:
            df_bt['Signal'] = np.where(df_bt['RSI'] < 40, 1, np.where(df_bt['RSI'] > 70, -1, 0))
            df_bt['Strategy_Returns'] = (df_bt['Signal'].shift(1) * df_bt['Price_Change'])
            cum_returns = (1 + df_bt['Strategy_Returns'].fillna(0)).cumprod() - 1
            st.metric("العائد الإجمالي", f"{cum_returns.iloc[-1]*100:.2f}%")

elif app_mode == "ماسح السوق الشامل (Market Screener)":
    st.title("🗺️ الماسح المؤسسي الشامل")
    s_input = st.text_area("قائمة العملات للمسح (مفصولة بفواصل):", value=", ".join(all_available_cryptos[:20]))
    assets_l = [x.strip().upper() if x.strip().upper().endswith("-USD") else f"{x.strip().upper()}-USD" for x in s_input.split(',')]
    
    if st.button("🚀 تشغيل الماسح"):
        res = []
        with st.spinner("جاري مسح الأصول..."):
            for ast in assets_l:
                df_temp = load_and_process_data(ast)
                if df_temp is not None and not df_temp.empty:
                    px_v = float(df_temp['Close'].iloc[-1])
                    rsi_v = float(df_temp['RSI'].iloc[-1])
                    res.append({"الأصل": ast, "السعر الحالي": f"${px_v:,.2f}", "RSI": f"{rsi_v:.1f}"})
        if res:
            st.table(pd.DataFrame(res))

elif app_mode == "سجل الصفقات الحي والأداء (Trade Journal & PnL)":
    st.title("📈 سجل الصفقات الحية")
    trades_df = get_trade_journal(st.session_state['username'])
    if not trades_df.empty:
        st.dataframe(trades_df, use_container_width=True)

else:
    with st.spinner(f"جاري جلب وتحليل البيانات لـ '{crypto_symbol}'..."):
        data = load_and_process_data(crypto_symbol, rsi_window=rsi_period_input)

    if data is None or data.empty:
        st.error(f"⚠️ لم يتم العثور على بيانات للرمز '{crypto_symbol}'. تأكد من الرمز (مثل: FLOKI أو BONK).")
    else:
        clean_data = data.dropna()
        X = np.nan_to_num(np.ascontiguousarray(clean_data[advanced_features].astype(float).values), nan=0.0)
        y = clean_data['Target'].astype(int).values
        
        model_instance = get_trained_model(model_algo_choice)
        
        # التعديل الهام لمنع الخطأ AttributeError
        if model_instance is not None:
            model_instance.fit(X, y)
            today_features = np.nan_to_num(np.ascontiguousarray(data[advanced_features].iloc[-1:].astype(float).values), nan=0.0)
            ensemble_probs = model_instance.predict_proba(today_features)[0]
            prediction = 1 if ensemble_probs[1] > ensemble_probs[0] else 0
            max_prob = max(ensemble_probs)
        else:
            prediction, max_prob = 1, 0.50

        current_price = float(data['Close'].iloc[-1])
        st.title(f"⚡ التحليل والتنبؤ النهائي لـ {crypto_symbol}")
        
        c1, c2 = st.columns(2)
        c1.metric("السعر اللحظي", f"${current_price:,.4f}" if current_price < 1 else f"${current_price:,.2f}")
        dec_str = "📈 شراء" if prediction == 1 and max_prob >= conf_threshold_input else "⚠️ ترقب"
        c2.metric("التوصية", dec_str, delta=f"نسبة الثقة: {max_prob*100:.1f}%")

        fig = go.Figure(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='السعر', line=dict(color='#00FFA3')))
        fig.update_layout(template="plotly_dark", height=400, title=f"رسم بياني لـ {crypto_symbol}")
        st.plotly_chart(fig, use_container_width=True)
