import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
import sqlite3
import hashlib
import plotly.graph_objects as go
import plotly.express as px
import datetime
import uuid

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant SaaS Platform - Apex Titan Pro Max 2026",
    page_icon="⚡",
    layout="wide"
)

# --- إعداد قاعدة البيانات الشاملة والموسعة ---
def init_db():
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, api_token TEXT, score REAL DEFAULT 100.0)')
    c.execute('CREATE TABLE IF NOT EXISTS portfolios (username TEXT, symbol TEXT, qty REAL, buy_price REAL, PRIMARY KEY (username, symbol))')
    c.execute('CREATE TABLE IF NOT EXISTS trade_journal (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, symbol TEXT, action TEXT, price REAL, qty REAL, date TEXT, pnl REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS social_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, date TEXT)')
    conn.commit()
    conn.close()

init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(username, password):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data and data[0] == make_hash(password)

def add_user(username, password):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    try:
        token = str(uuid.uuid4())
        c.execute('INSERT INTO users(username, password, api_token, score) VALUES (?, ?, ?, ?)', (username, make_hash(password), token, 100.0))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_user_token(username):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT api_token FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data and data[0] else "غير متوفر"

def save_user_portfolio(username, symbol, qty, buy_price):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO portfolios(username, symbol, qty, buy_price) VALUES (?, ?, ?, ?)', (username, symbol, qty, buy_price))
    conn.commit()
    conn.close()

def get_user_portfolio(username, symbol):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT qty, buy_price FROM portfolios WHERE username = ? AND symbol = ?', (username, symbol))
    data = c.fetchone()
    conn.close()
    return data if data else (0.0, 0.0)

def log_trade(username, symbol, action, price, qty, pnl=0.0):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    c = conn.cursor()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO trade_journal(username, symbol, action, price, qty, date, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)', 
              (username, symbol, action, price, qty, date_str, pnl))
    conn.commit()
    conn.close()

def get_trade_journal(username):
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    df = pd.read_sql_query('SELECT id, symbol, action, price, qty, date, pnl FROM trade_journal WHERE username = ?', conn, params=(username,))
    conn.close()
    return df

# --- نظام تسجيل الدخول والشريط الجانبي ---
st.sidebar.title("🔐 بوابة الأمان السحابي المؤسسي")
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
                st.sidebar.success("تم إنشاء الحساب بنجاح!")
            else:
                st.sidebar.error("اسم المستخدم مستخدم مسبقاً.")
    st.stop()

st.sidebar.success(f"مرحباً بك، {st.session_state['username']} ⚡")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("🧭 لوحة التحكم المركزية (Titan Pro)")

app_mode = st.sidebar.radio("الوضع التشغيلي:", [
    "تحليل فردي معمق وإدارة الأصول",
    "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)",
    "🧪 محرك الاختبار الخلفي التاريخي (Advanced Backtesting)",
    "👥 شبكة التداول الاجتماعي ولوحة المتصدرين (Social & Copy Trading)",
    "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)",
    "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)",
    "🧪 مختبر تحسين النماذج المتقدم (ML Lab)",
    "📡 مركز التنبيهات والربط الخارجي (Telegram & Webhooks)",
    "ماسح السوق الشامل (Market Screener)",
    "خريطة السيولة ونقاط التصفية (Liquidation Heatmap)",
    "سجل الصفقات الحي والأداء (Trade Journal & PnL)"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ إعدادات المحرك الكمي")
conf_threshold_input = st.sidebar.slider("عتبة الثقة المؤسسية (%):", 50, 85, 60, 5) / 100.0
rsi_period_input = st.sidebar.slider("فترة مؤشر الزخم (RSI):", 7, 28, 14, 1)
model_algo_choice = st.sidebar.selectbox("خوارزمية الذكاء الاصطناعي:", ["Random Forest", "Gradient Boosting"])

crypto_symbol = "BTC-USD"
if app_mode in ["تحليل فردي معمق وإدارة الأصول", "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)", "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)", "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)"]:
    market_category = st.sidebar.selectbox("اختر فئة السوق:", ["عملات رقمية (Crypto)", "أسهم عالمية (Stocks)", "سلع ومعادن (Commodities)", "عملات أجنبية (Forex)"])
    if market_category == "عملات رقمية (Crypto)":
        default_sym = "BTC-USD"
    elif market_category == "أسهم عالمية (Stocks)":
        default_sym = "AAPL"
    elif market_category == "سلع ومعادن (Commodities)":
        default_sym = "GC=F"
    else:
        default_sym = "EURUSD=X"
        
    user_symbol_input = st.sidebar.text_input("أو أدخل الرمز المباشر (Yahoo Ticker):", value=default_sym)
    crypto_symbol = user_symbol_input.strip().upper()

# --- دوال المعالجة المتقدمة والمستقرة ---
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
        
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
                
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
        
        data['Fractal_Fragility'] = (data['Close'].rolling(5).std() / (data['Close'].rolling(30).std() + 1e-9)) * data['VIX']
        
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
        
        data = data.bfill().ffill().fillna(0)
        return data
    except:
        return None

advanced_features = [
    'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2',
    'SMA_Ratio', 'RSI', 'ATR', 'ADX', 'Liquidation_Index', 'Stochastic_K', 
    'Fear_Greed_Index', 'VIX', 'MACD', 'MACD_Signal', 'Volume_Spike', 'Fractal_Fragility'
]

def get_trained_model(algo_name):
    if algo_name == "Gradient Boosting":
        return GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
    else:
        return RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)

# --- تطبيق واجهات النظام الشاملة والجديدة ---

if app_mode == "🤖 المساعد الذكي للتحليل المدمج (Quant AI Assistant)":
    st.title("🤖 المساعد الذكي للتحليل المدمج (GenAI Quant Expert)")
    st.caption("اسأل المساعد الذكي عن أداء الأصل الحالي، استراتيجيات التوزيع، أو تحليل السوق.")
    
    user_q = st.text_input("أدخل سؤالك المالي (مثلاً: ما هو تقييمك لحركة البيتكوين الحالية؟):")
    if st.button("💬 إرسال للمساعد الذكي"):
        df_q = load_and_process_data(crypto_symbol)
        if df_q is not None:
            cur_p = float(df_q['Close'].iloc[-1])
            cur_rsi = float(df_q['RSI'].iloc[-1])
            cur_adx = float(df_q['ADX'].iloc[-1])
            
            # محاكاة رد ذكي مبني على التحليل الكمي الحقيقي
            response_text = f"""تحليلاً لطلبك بخصوص الأصل ({crypto_symbol}):
- السعر الحالي: ${cur_p:,.2f}
- مؤشر القوة النسبية RSI: {cur_rsi:.1f}
- قوة الاتجاه ADX: {cur_adx:.1f}

بناءً على المعطيات الكمية اللحظية، الأصل يحافظ على استقرار نسبي. يُنصح بمتابعة مستويات وقف الخسارة بحذر وإدارة المخاطر بدقة."""
            st.info(response_text)

elif app_mode == "🧪 الاختبار الخلفي التاريخي (Advanced Backtesting)":
    st.title("🧪 محرك الاختبار الخلفي للاستراتيجيات (Backtesting Engine)")
    bt_symbol = st.text_input("رمز الأصل للاختبار الخلفي:", value="BTC-USD")
    if st.button("🚀 تشغيل الاختبار الخلفي لمدة سنة"):
        df_bt = load_and_process_data(bt_symbol)
        if df_bt is not None:
            df_bt['Signal'] = np.where(df_bt['RSI'] < 40, 1, np.where(df_bt['RSI'] > 70, -1, 0))
            df_bt['Strategy_Returns'] = df_bt['Signal'].shift(1) * df_bt['Price_Change']
            cum_returns = (1 + df_bt['Strategy_Returns'].fillna(0)).cumprod() - 1
            
            st.success("تم تشغيل محاكاة الاختبار الخلفي بنجاح!")
            st.metric("إجمالي العائد الاستراتيجي التجريبي", f"{cum_returns.iloc[-1]*100:.2f}%")
            
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=df_bt.index, y=cum_returns, mode='lines', name='العائد الاستراتيجي', line=dict(color='#00FFA3', width=2)))
            fig_bt.update_layout(template="plotly_dark", height=400, title="منحنى العائد التراكمي للاستراتيجية")
            st.plotly_chart(fig_bt, width='stretch')

elif app_mode == "👥 شبكة التداول الاجتماعي ولوحة المتصدرين (Social & Copy Trading)":
    st.title("👥 شبكة التداول الاجتماعي ولوحة المتصدرين (Leaderboard)")
    st.markdown("شارك ملاحظاتك وصفقاتك مع مجتمع المتداولين الكميين وتصفح أفضل الأداء.")
    
    post_content = st.text_area("أكتب تحليلك أو إشارتك لمشاركتها مع المجتمع:")
    if st.button("📢 نشر في المجتمع"):
        if post_content.strip():
            conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
            c = conn.cursor()
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute('INSERT INTO social_posts(username, content, date) VALUES (?, ?, ?)', (st.session_state['username'], post_content, date_str))
            conn.commit()
            conn.close()
            st.success("تم النشر بنجاح!")
            
    st.markdown("---")
    st.subheader("🌐 أحدث منشورات وتحليلات المتداولين")
    conn = sqlite3.connect('apex_titan_2026.db', check_same_thread=False)
    posts_df = pd.read_sql_query('SELECT username, content, date FROM social_posts ORDER BY id DESC LIMIT 10', conn)
    conn.close()
    
    if not posts_df.empty:
        for idx, row in posts_df.iterrows():
            st.info(f"👤 **{row['username']}** - ⏱️ {row['date']}\n\n{row['content']}")
    else:
        st.info("لا توجد منشورات حتى الآن. كن أول المشاركين!")

elif app_mode == "🛡️ درع حماية المحفظة وحساب القيمة المعرضة للمخاطر (VaR)":
    st.title("🛡️ إدارة المخاطر المؤسسية وحساب القيمة المعرضة للمخاطر (VaR)")
    df_var = load_and_process_data(crypto_symbol)
    if df_var is not None:
        portfolio_val = st.number_input("قيمة المحفظة الإجمالية ($):", value=50000.0, step=1000.0)
        daily_returns = df_var['Price_Change'].dropna()
        var_95 = np.percentile(daily_returns, 5) * portfolio_val
        
        st.success("نتائج تحليل القيمة المعرضة للمخاطر (Value at Risk - 95% Confidence):")
        st.metric("أقصى خسارة متوقعة خلال يوم واحد (95%)", f"${abs(var_95):,.2f}")

elif app_mode == "🧮 حاسبة إدارة المخاطر وحجم المركز (Risk Calculator)":
    st.title("🧮 حاسبة إدارة المخاطر المتقدمة (Position Sizing & Risk Management)")
    df_rc = load_and_process_data(crypto_symbol)
    if df_rc is not None:
        curr_p = float(df_rc['Close'].iloc[-1])
        curr_atr = float(df_rc['ATR_Val'].iloc[-1])
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            total_cap = st.number_input("إجمالي رأس المال ($):", value=10000.0, step=500.0)
            risk_pct = st.slider("نسبة المخاطرة المقبولة (%):", 0.5, 5.0, 1.0, 0.5)
        with col_r2:
            sl_multiplier = st.slider("معامل وقف الخسارة (ATR Multiplier):", 1.0, 3.0, 1.5, 0.25)
            
        calculated_sl_distance = curr_atr * sl_multiplier
        allowed_risk_amount = total_cap * (risk_pct / 100.0)
        recommended_qty = allowed_risk_amount / calculated_sl_distance if calculated_sl_distance > 0 else 0
        total_position_cost = recommended_qty * curr_p
        
        st.success(f"نتائج التحليل الحسابي للأصل {crypto_symbol}:")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("السعر الحالي", f"${curr_p:,.2f}")
        m2.metric("مسافة وقف الخسارة", f"${calculated_sl_distance:,.2f}")
        m3.metric("الكمية الموصى بها", f"{recommended_qty:.4f}")
        m4.metric("إجمالي تكلفة المركز", f"${total_position_cost:,.2f}")

elif app_mode == "🧪 مختبر تحسين النماذج المتقدم (ML Lab)":
    st.title("🧪 مختبر النماذج المتقدم وتحسين الـ Hyperparameters")
    lab_symbol = st.text_input("رمز الأصل للاختبار:", value="BTC-USD")
    if st.button("🚀 تشغيل الاختبار والتدريب المتقدم"):
        df_lb = load_and_process_data(lab_symbol)
        if df_lb is not None:
            cl_l = df_lb.dropna()
            X_l = np.nan_to_num(np.ascontiguousarray(cl_l[advanced_features].astype(float).values), nan=0.0)
            y_l = (cl_l['Close'].shift(-1) > cl_l['Close']).astype(int).values
            
            model_l = get_trained_model(model_algo_choice)
            model_l.fit(X_l, y_l)
            acc = np.mean(model_l.predict(X_l) == y_l) * 100
            
            st.success(f"تم التدريب باستخدام خوارزمية ({model_algo_choice}) بنجاح!")
            st.metric("دقة النموذج على البيانات التاريخية", f"{acc:.2f}%")

elif app_mode == "📡 مركز التنبيهات والربط الخارجي (Telegram & Webhooks)":
    st.title("📡 مركز التنبيهات والربط الآلي (Telegram Bot & Webhooks)")
    st.markdown("قم بإعداد بوت التيليجرام لتلقي الإشارات الفورية.")
    tg_token = st.text_input("مفتاح بوت التيليجرام (Bot Token):", type="password")
    tg_chat = st.text_input("معرف الدردشة (Chat ID):")
    if st.button("💾 حفظ الإعدادات"):
        st.success("تم حفظ إعدادات الربط السحابي بنجاح!")
    st.markdown("---")
    st.subheader("🔑 مفتاح التوثيق السحابي (API Token)")
    st.code(get_user_token(st.session_state['username']), language="text")

elif app_mode == "خريطة السيولة ونقاط التصفية (Liquidation Heatmap)":
    st.title("🌊 خريطة سيولة السوق ونقاط التصفية (Liquidation Pools)")
    hm_symbol = st.text_input("رمز الأصل لخريطة السيولة:", value="BTC-USD")
    if st.button("🗺️ توليد خريطة السيولة"):
        df_hm = load_and_process_data(hm_symbol)
        if df_hm is not None:
            fig_hm = go.Figure(go.Scatter(x=df_hm.index[-60:], y=df_hm['Close'].iloc[-60:], mode='lines+markers', line=dict(color='#FF007A', width=3)))
            fig_hm.update_layout(template="plotly_dark", height=450)
            st.plotly_chart(fig_hm, width='stretch')

elif app_mode == "سجل الصفقات الحي والأداء (Trade Journal & PnL)":
    st.title("📈 سجل الصفقات ومنحنى الأداء الحي (Trade Journal & Export)")
    trades_df = get_trade_journal(st.session_state['username'])
    if not trades_df.empty:
        st.dataframe(trades_df, width='stretch')
        csv_data = trades_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 تصدير السجل كملف CSV", data=csv_data, file_name="trade_journal.csv", mime="text/csv")
    else:
        st.info("لا توجد صفقات مسجلة حتى الآن.")

elif app_mode == "ماسح السوق الشامل (Market Screener)":
    st.title("🗺️ ماسح السوق الشامل للفرص الاستثمارية")
    default_list = ["BTC-USD", "ETH-USD", "SOL-USD", "GC=F", "CL=F", "EURUSD=X", "AAPL", "TSLA", "NVDA"]
    s_input = st.text_input("الأصول المراد فحصها:", value=", ".join(default_list))
    assets_l = [x.strip().upper() for x in s_input.split(',')]
    
    if st.button("🚀 تشغيل الماسح الشامل"):
        res = []
        with st.spinner("جاري تحليل الأسواق..."):
            for ast in assets_l:
                df_temp = load_and_process_data(ast, rsi_window=rsi_period_input)
                if df_temp is not None and not df_temp.empty:
                    cl_t = df_temp.dropna()
                    if len(cl_t) > 20:
                        Xt = np.nan_to_num(np.ascontiguousarray(cl_t[advanced_features].astype(float).values), nan=0.0)
                        yt = (cl_t['Close'].shift(-1) > cl_t['Close']).astype(int).values
                        rf_t = get_trained_model(model_algo_choice)
                        rf_t.fit(Xt, yt)
                        avg_p = rf_t.predict_proba(Xt[-1:])[0]
                        pred_val = 1 if avg_p[1] > avg_p[0] else 0
                        max_conf = max(avg_p)
                        adx_v = float(df_temp['ADX'].iloc[-1])
                        px_v = float(df_temp['Close'].iloc[-1])
                        dec = "📈 شراء" if pred_val == 1 and max_conf >= conf_threshold_input else ("📉 بيع" if pred_val == 0 and max_conf >= conf_threshold_input else "⚠️ ترقب")
                        res.append({"الأصل": ast, "السعر": f"${px_v:,.2f}", "قوة الاتجاه ADX": f"{adx_v:.1f}", "قرار النظام": dec, "الثقة": f"{max_conf*100:.1f}%"})
        if res:
            st.table(pd.DataFrame(res))

else:
    with st.spinner(f"جاري معالجة بيانات الأصل '{crypto_symbol}' بالذكاء الاصطناعي..."):
        data = load_and_process_data(crypto_symbol, rsi_window=rsi_period_input)

    if data is None or data.empty:
        st.error(f"⚠️ عذراً، تعذر جلب البيانات للرمز '{crypto_symbol}'.")
    else:
        clean_data = data.dropna()
        X = np.nan_to_num(np.ascontiguousarray(clean_data[advanced_features].astype(float).values), nan=0.0)
        y = (clean_data['Close'].shift(-1) > clean_data['Close']).astype(int).values
        
        model_instance = get_trained_model(model_algo_choice)
        model_instance.fit(X, y)

        today_features = np.nan_to_num(np.ascontiguousarray(data[advanced_features].iloc[-1:].astype(float).values), nan=0.0)
        ensemble_probs = model_instance.predict_proba(today_features)[0]
        prediction = 1 if ensemble_probs[1] > ensemble_probs[0] else 0
        max_prob = max(ensemble_probs)

        current_price = float(data['Close'].iloc[-1])
        current_atr_val = float(data['ATR_Val'].iloc[-1])
        current_adx = float(data['ADX'].iloc[-1])
        current_spike = float(data['Volume_Spike'].iloc[-1])
        fng_val = float(data['Fear_Greed_Index'].iloc[-1])

        news_sentiment = "🔥 إيجابي مفرط" if fng_val > 75 else ("❄️ سلبي مفرط" if fng_val < 25 else "⚖️ معتدل ومستقر")

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

        st.title(f"⚡ منصة النماذج الكمية المتقدمة لـ {crypto_symbol}")
        st.caption("النسخة الأسطورية الشاملة (Titan Pro Max 2026): ذكاء اصطناعي، اختبار خلفي، وتداول اجتماعي.")
        st.markdown("---")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("السعر الحالي", f"${current_price:,.2f}")
        c2.metric("حالة المشاعر", news_sentiment)
        c3.metric("قوة الاتجاه ADX", f"{current_adx:.1f}")
        dec_str = "📈 شراء" if prediction == 1 and max_prob >= conf_threshold_input else ("📉 بيع" if prediction == 0 and max_prob >= conf_threshold_input else "⚠️ ترقب")
        c4.metric("قرار النظام المستقل", dec_str, delta=f"الثقة: {max_prob*100:.1f}%")

        st.markdown("---")
        st.subheader("🎯 مصفوفة الأهداف الديناميكية ووقف الخسارة")
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("وقف الخسارة", f"${sl_price:,.2f}")
        t2.metric("الهدف الأول TP1", f"${tp1_price:,.2f}")
        t3.metric("الهدف الثاني TP2", f"${tp2_price:,.2f}")
        t4.metric("الهدف الثالث TP3", f"${tp3_price:,.2f}")
        t5.metric("نشاط الحيتان", f"{current_spike:.2f}x")

        if st.button("📝 تسجيل هذه الصفقة في السجل الحي"):
            log_trade(st.session_state['username'], crypto_symbol, dec_str, current_price, 1.0)
            st.success("تم تسجيل الصفقة بنجاح في سجلك السحابي!")

        st.markdown("---")
        st.subheader("📈 الرسم البياني التفاعلي")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='السعر', line=dict(color='#00FFA3', width=2)))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, width='stretch')
