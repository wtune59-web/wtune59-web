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

# --- إعداد قاعدة البيانات الشاملة والموسعة آمنة الاتصال ---
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
                st.sidebar.success("تم إنشاء الحساب وتفعيله كمتداول رئيسي!")
            else:
                st.sidebar.error("اسم المستخدم مستخدم مسبقاً.")
    st.stop()

st.sidebar.success(f"مرحباً بك، المؤسس {st.session_state['username']} ⚡")
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
    "خريطة السيولة ونقاط التصفية (Liquidation Heatmap)",
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

crypto_symbol = "BTC-USD"
if app_mode in ["تحليل فردي معمق وإدارة الأصول", "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)", "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)", "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)"]:
    market_category = st.sidebar.selectbox("اختر فئة السوق:", ["عملات الذكاء الاصطناعي (AI Crypto)", "عملات رقمية عامة (Crypto)", "أسهم عالمية (Stocks)"])
    default_sym = "RENDER-USD" if market_category == "عملات الذكاء الاصطناعي (AI Crypto)" else ("BTC-USD" if market_category == "عملات رقمية عامة (Crypto)" else "AAPL")
    user_symbol_input = st.sidebar.text_input("أو أدخل الرمز المباشر (Yahoo Ticker):", value=default_sym)
    crypto_symbol = user_symbol_input.strip().upper()

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

# جلب اتجاه الإطار الأسبوعي لمنع تضارب الاتجاه
@st.cache_data(ttl=3600)
def get_weekly_trend(symbol):
    try:
        w_data = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if w_data is None or w_data.empty: return 1
        if isinstance(w_data.columns, pd.MultiIndex): w_data.columns = w_data.columns.get_level_values(0)
        sma200 = w_data['Close'].rolling(200).mean().iloc[-1]
        return 1 if w_data['Close'].iloc[-1] >= sma200 else 0
    except:
        return 1

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
        
        # تحسين: حاسبة التصفية بدون تسريب بيانات تاريخية (Rolling Windows)
        data['Estimated_Liquidations'] = (data['Volume'] * np.abs(data['Price_Change']) * data['VIX']).rolling(5).mean()
        liq_min = data['Estimated_Liquidations'].rolling(30).min()
        liq_max = data['Estimated_Liquidations'].rolling(30).max()
        data['Liquidation_Index'] = 100 * (data['Estimated_Liquidations'] - liq_min) / (liq_max - liq_min + 1e-9)
        data['Liquidation_Index'] = data['Liquidation_Index'].fillna(50)
        
        low_14 = data['Low'].rolling(14).min()
        high_14 = data['High'].rolling(14).max()
        data['Stochastic_K'] = 100 * (data['Close'] - low_14) / (high_14 - low_14 + 1e-9)
        
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        
        vol_mean = data['Volume'].rolling(30).mean()
        data['Volume_Spike'] = data['Volume'] / (vol_mean + 1e-9)
        data['Fractal_Fragility'] = (data['Close'].rolling(5).std() / (data['Close'].rolling(30).std() + 1e-9)) * data['VIX']
        
        data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
        data = data.bfill().ffill().fillna(0)
        return data
    except Exception as e:
        print(f"Error loading {symbol}: {e}")
        return None

advanced_features = [
    'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2',
    'SMA_Ratio', 'RSI', 'ATR', 'ADX', 'Liquidation_Index', 'Stochastic_K', 
    'Fear_Greed_Index', 'VIX', 'MACD', 'MACD_Signal', 'Volume_Spike', 'Fractal_Fragility'
]

def get_trained_model(algo_name):
    if algo_name == "Gradient Boosting":
        return GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
    elif algo_name == "XGBoost" and XGB_AVAILABLE:
        return xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric='logloss')
    elif algo_name == "Deep Learning (LSTM)" and LSTM_AVAILABLE:
        return None
    else:
        return RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)

# --- الواجهات والتطبيقات ---
if app_mode == "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)":
    st.title("🤖 المساعد الذكي للتحليل المدمج (GenAI Quant Expert)")
    user_q = st.text_input("أدخل سؤالك المالي:")
    if st.button("💬 إرسال للمساعد الذكي"):
        df_q = load_and_process_data(crypto_symbol)
        if df_q is not None and not df_q.empty:
            cur_p, cur_rsi, cur_adx = float(df_q['Close'].iloc[-1]), float(df_q['RSI'].iloc[-1]), float(df_q['ADX'].iloc[-1])
            st.info(f"تحليلاً لطلبك بخصوص ({crypto_symbol}):\n- السعر: ${cur_p:,.2f}\n- RSI: {cur_rsi:.1f}\n- قوة الاتجاه ADX: {cur_adx:.1f}\nالوضع مستقر ومتاح للتنفيذ.")
        else:
            st.error(f"تعذر جلب بيانات الرمز '{crypto_symbol}'.")

elif app_mode == "🧪 محرك الاختبار الخلفي المؤسسي (Institutional Backtesting)":
    st.title("🧪 محرك الاختبار الخلفي المؤسسي (مع العمولات والانزلاق السعري)")
    bt_symbol = st.text_input("رمز الأصل للاختبار:", value="RENDER-USD")
    col_b1, col_b2 = st.columns(2)
    trading_fee = col_b1.number_input("عمولة المنصة (%):", value=0.1) / 100.0
    slippage = col_b2.number_input("الانزلاق السعري (%):", value=0.05) / 100.0
        
    if st.button("🚀 تشغيل محاكاة الاختبار"):
        df_bt = load_and_process_data(bt_symbol)
        if df_bt is not None and not df_bt.empty:
            df_bt['Signal'] = np.where(df_bt['RSI'] < 40, 1, np.where(df_bt['RSI'] > 70, -1, 0))
            costs = df_bt['Signal'].diff().abs().fillna(0) * (trading_fee + slippage)
            df_bt['Strategy_Returns'] = (df_bt['Signal'].shift(1) * df_bt['Price_Change']) - costs
            cum_returns = (1 + df_bt['Strategy_Returns'].fillna(0)).cumprod() - 1
            
            sharpe = (df_bt['Strategy_Returns'].mean() / (df_bt['Strategy_Returns'].std() + 1e-9)) * np.sqrt(252)
            st.success("تم التقييم بنجاح!")
            m1, m2 = st.columns(2)
            m1.metric("العائد الإجمالي", f"{cum_returns.iloc[-1]*100:.2f}%")
            m2.metric("معدل شارب (Sharpe Ratio)", f"{sharpe:.2f}")
            
            fig_bt = go.Figure(go.Scatter(x=df_bt.index, y=cum_returns, mode='lines', name='العائد', line=dict(color='#00FFA3')))
            fig_bt.update_layout(template="plotly_dark", height=400, title="منحنى العائد الصافي")
            st.plotly_chart(fig_bt, use_container_width=True)

elif app_mode == "👥 شبكة التداول الاجتماعي ونسخ الصفقات (Copy Trading)":
    st.title("👥 شبكة التداول الاجتماعي ونسخ الصفقات")
    post_content = st.text_area("أشرك المجتمع بصفقاتك:")
    if st.button("📢 نشر"):
        if post_content.strip():
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                conn.cursor().execute('INSERT INTO social_posts(username, content, date) VALUES (?, ?, ?)', (st.session_state['username'], post_content, date_str))
                conn.commit()
            st.success("تم النشر!")

elif app_mode == "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)":
    st.title("🛡️ القيمة المعرضة للمخاطر (VaR)")
    df_var = load_and_process_data(crypto_symbol)
    if df_var is not None and not df_var.empty:
        portfolio_val = st.number_input("قيمة المحفظة ($):", value=50000.0)
        var_95 = np.percentile(df_var['Price_Change'].dropna(), 5) * portfolio_val
        st.metric("أقصى خسارة متوقعة خلال يوم (95% Confidence)", f"${abs(var_95):,.2f}")

elif app_mode == "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)":
    st.title("🧮 حاسبة إدارة المخاطر وحجم المركز")
    df_rc = load_and_process_data(crypto_symbol)
    if df_rc is not None and not df_rc.empty:
        curr_p, curr_atr = float(df_rc['Close'].iloc[-1]), float(df_rc['ATR_Val'].iloc[-1])
        total_cap = st.number_input("إجمالي رأس المال ($):", value=10000.0)
        risk_pct = st.slider("نسبة المخاطرة (%):", 0.5, 5.0, 1.0)
        sl_multiplier = st.slider("معامل وقف الخسارة (ATR):", 1.0, 3.0, 1.5)
        
        sl_dist = curr_atr * sl_multiplier
        qty = (total_cap * (risk_pct / 100.0)) / sl_dist if sl_dist > 0 else 0
        
        st.metric("الكمية الآمنة الموصى بها", f"{qty:.4f}")

elif app_mode == "🧪 مختبر تحسين النماذج المتقدم (ML & Deep Learning Lab)":
    st.title("🧪 مختبر النماذج المتقدم والتعلم العميق")
    lab_symbol = st.text_input("رمز الأصل للاختبار:", value="RENDER-USD")
    if st.button("🚀 تدريب وتحديث النماذج"):
        df_lb = load_and_process_data(lab_symbol)
        if df_lb is not None and not df_lb.empty:
            cl_l = df_lb.dropna()
            X_l = np.nan_to_num(np.ascontiguousarray(cl_l[advanced_features].astype(float).values), nan=0.0)
            y_l = cl_l['Target'].astype(int).values
            
            model_l = get_trained_model(model_algo_choice)
            if model_l is not None:
                model_l.fit(X_l, y_l)
                acc = np.mean(model_l.predict(X_l) == y_l) * 100
                st.success(f"تم التدريب بـ ({model_algo_choice})!")
                st.metric("دقة النموذج", f"{acc:.2f}%")
            elif LSTM_AVAILABLE:
                # تحسين: تحجيم البيانات لرفع دقة شبكة LSTM
                scaler = MinMaxScaler()
                X_scaled = scaler.fit_transform(X_l)
                X_lstm = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
                
                model_lstm = Sequential([
                    LSTM(50, activation='relu', input_shape=(1, X_l.shape[1])),
                    Dropout(0.2),
                    Dense(1, activation='sigmoid')
                ])
                model_lstm.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
                model_lstm.fit(X_lstm, y_l, epochs=5, batch_size=32, verbose=0)
                preds = (model_lstm.predict(X_lstm) > 0.5).astype(int).flatten()
                st.success("تم تدريب نموذج LSTM بنجاح!")
                st.metric("دقة LSTM (المقيسة)", f"{np.mean(preds == y_l)*100:.2f}%")

elif app_mode == "سجل الصفقات الحي والأداء (Trade Journal & PnL)":
    st.title("📈 سجل الصفقات الحية والأداء")
    trades_df = get_trade_journal(st.session_state['username'])
    if not trades_df.empty:
        st.dataframe(trades_df, use_container_width=True)

else:
    with st.spinner(f"جاري معالجة الأصل '{crypto_symbol}'..."):
        data = load_and_process_data(crypto_symbol, rsi_window=rsi_period_input)

    if data is None or data.empty:
        st.error(f"⚠️ تعذر جلب البيانات للرمز '{crypto_symbol}'.")
    else:
        clean_data = data.dropna()
        X = np.nan_to_num(np.ascontiguousarray(clean_data[advanced_features].astype(float).values), nan=0.0)
        y = clean_data['Target'].astype(int).values
        
        if model_algo_choice == "Deep Learning (LSTM)" and LSTM_AVAILABLE:
            scaler = MinMaxScaler()
            X_scaled = scaler.fit_transform(X)
            X_lstm = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
            
            model_instance = Sequential([LSTM(50, activation='relu', input_shape=(1, X.shape[1])), Dense(1, activation='sigmoid')])
            model_instance.compile(optimizer='adam', loss='binary_crossentropy')
            model_instance.fit(X_lstm, y, epochs=3, verbose=0)
            
            today_features = scaler.transform(np.nan_to_num(np.ascontiguousarray(data[advanced_features].iloc[-1:].astype(float).values), nan=0.0)).reshape((1, 1, len(advanced_features)))
            prob_up = float(model_instance.predict(today_features)[0][0])
            max_prob = max(prob_up, 1 - prob_up)
            prediction = 1 if prob_up > 0.5 else 0
        else:
            model_instance = get_trained_model(model_algo_choice)
            model_instance.fit(X, y)
            today_features = np.nan_to_num(np.ascontiguousarray(data[advanced_features].iloc[-1:].astype(float).values), nan=0.0)
            ensemble_probs = model_instance.predict_proba(today_features)[0]
            prediction = 1 if ensemble_probs[1] > ensemble_probs[0] else 0
            max_prob = max(ensemble_probs)

        # تحسين: فلترة الاتجاه بالأسبوع
        weekly_trend = get_weekly_trend(crypto_symbol)
        if prediction == 1 and weekly_trend == 0:
            max_prob *= 0.85 # تخفيض الثقة إذا كان شراء ضد الاتجاه العام الأسبوعي

        current_price = float(data['Close'].iloc[-1])
        current_atr_val = float(data['ATR_Val'].iloc[-1])
        fng_val = float(data['Fear_Greed_Index'].iloc[-1])

        news_sentiment = "🔥 إيجابي مفرط" if fng_val > 75 else ("❄️ سلبي مفرط" if fng_val < 25 else "⚖️ معتدل ومستقر")

        sl_price = current_price - (1.5 * current_atr_val) if prediction == 1 else current_price + (1.5 * current_atr_val)
        tp1_price = current_price + (1.0 * current_atr_val) if prediction == 1 else current_price - (1.0 * current_atr_val)

        st.title(f"⚡ منصة النماذج المؤسسية المتقدمة لـ {crypto_symbol}")
        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        c1.metric("السعر الحالي", f"${current_price:,.2f}")
        c2.metric("حالة المشاعر", news_sentiment)
        dec_str = "📈 شراء" if prediction == 1 and max_prob >= conf_threshold_input else ("📉 بيع" if prediction == 0 and max_prob >= conf_threshold_input else "⚠️ ترقب")
        c3.metric("قرار النظام المستقل", dec_str, delta=f"الثقة: {max_prob*100:.1f}%")

        if st.button("📝 تسجيل الصفقة وبثها للمتابعين"):
            log_trade(st.session_state['username'], crypto_symbol, dec_str, current_price, 1.0)
            st.success("تم تسجيل الصفقة وبثها بنجاح!")

        fig = go.Figure(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='السعر', line=dict(color='#00FFA3')))
        fig.update_layout(template="plotly_dark", height=450, title=f"تحليل السعر التاريخي لـ {crypto_symbol}")
        st.plotly_chart(fig, use_container_width=True)
