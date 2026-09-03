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
import datetime

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant SaaS Platform - Apex Elite Edition",
    page_icon="⚡",
    layout="wide"
)

# --- إعداد قاعدة البيانات الشاملة ---
def init_db():
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS portfolios (username TEXT, symbol TEXT, qty REAL, buy_price REAL, PRIMARY KEY (username, symbol))')
    c.execute('CREATE TABLE IF NOT EXISTS bot_settings (username TEXT PRIMARY KEY, api_key TEXT, api_secret TEXT, auto_trade_enabled INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS trade_journal (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, symbol TEXT, action TEXT, price REAL, qty REAL, date TEXT, pnl REAL)')
    conn.commit()
    conn.close()

init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(username, password):
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data and data[0] == make_hash(password)

def add_user(username, password):
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
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
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO portfolios(username, symbol, qty, buy_price) VALUES (?, ?, ?, ?)', (username, symbol, qty, buy_price))
    conn.commit()
    conn.close()

def get_user_portfolio(username, symbol):
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT qty, buy_price FROM portfolios WHERE username = ? AND symbol = ?', (username, symbol))
    data = c.fetchone()
    conn.close()
    return data if data else (0.0, 0.0)

def log_trade(username, symbol, action, price, qty):
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    c = conn.cursor()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO trade_journal(username, symbol, action, price, qty, date, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)', 
              (username, symbol, action, price, qty, date_str, 0.0))
    conn.commit()
    conn.close()

def get_trade_journal(username):
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    df = pd.read_sql_query('SELECT symbol, action, price, qty, date, pnl FROM trade_journal WHERE username = ?', conn, params=(username,))
    conn.close()
    return df

# --- نظام تسجيل الدخول والشريط الجانبي ---
st.sidebar.title("🔐 بوابة الأمان السحابي")
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
st.sidebar.title("🧭 لوحة التحكم المركزية")

app_mode = st.sidebar.radio("الوضع التشغيلي:", [
    "تحليل فردي معمق وإدارة الأصول",
    "ماسح السوق الشامل (Market Screener)",
    "مصفوفة مقارنة الأسواق والـ MPT",
    "سجل الصفقات الحي والأداء (Trade Journal & PnL)",
    "غرفة التداول الآلي (Auto-Trading API)"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ تخصيص المحرك الكمي")
conf_threshold_input = st.sidebar.slider("عتبة الثقة المؤسسية (%):", 50, 85, 60, 5) / 100.0
rsi_period_input = st.sidebar.slider("فترة مؤشر الزخم (RSI):", 7, 28, 14, 1)

crypto_symbol = "BTC-USD"
if app_mode == "تحليل فردي معمق وإدارة الأصول":
    market_category = st.sidebar.selectbox("اختر فئة السوق:", ["عملات رقمية (Crypto)", "أسهم عالمية (Stocks)", "سلع ومعادن (Commodities)", "عملات أجنبية (Forex)"])
    if market_category == "عملات رقمية (Crypto)":
        default_sym = "BTC-USD"
    elif market_category == "أسهم عالمية (Stocks)":
        default_sym = "AAPL"
    elif market_category == "سلع ومعادن (Commodities)":
        default_sym = "GC=F" # الذهب
    else:
        default_sym = "EURUSD=X"
        
    user_symbol_input = st.sidebar.text_input("أو أدخل الرمز المباشر (Yahoo Ticker):", value=default_sym)
    crypto_symbol = user_symbol_input.strip().upper()
    
    saved_qty, saved_buy = get_user_portfolio(st.session_state['username'], crypto_symbol)
    st.sidebar.markdown("---")
    st.sidebar.header("💼 إدارة المحفظة الفردية")
    portfolio_qty = st.sidebar.number_input("الكمية:", min_value=0.0, value=float(saved_qty), step=0.01)
    portfolio_buy_price = st.sidebar.number_input("متوسط الشراء ($):", min_value=0.0, value=float(saved_buy), step=10.0)
    
    if st.sidebar.button("💾 حفظ المحفظة"):
        save_user_portfolio(st.session_state['username'], crypto_symbol, portfolio_qty, portfolio_buy_price)
        st.sidebar.success("تم الحفظ بنجاح!")

# --- دوال المعالجة المتقدمة ---
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

# --- واجهات المنصة المختلفة ---

if app_mode == "غرفة التداول الآلي (Auto-Trading API)":
    st.title("🤖 غرفة التداول الآلي التنفيذي")
    st.caption("ربط المنصة بحسابات المنصات الخارجية لتنفيذ إشارات الذكاء الاصطناعي بشكل آلي.")
    st.markdown("---")
    
    conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT api_key, api_secret, auto_trade_enabled FROM bot_settings WHERE username = ?', (st.session_state['username'],))
    b_data = c.fetchone()
    conn.close()
    b_key, b_sec, b_en = b_data if b_data else ("", "", 0)
    
    with st.form("auto_form"):
        apiKey = st.text_input("مفتاح API:", value=b_key, type="password")
        apiSec = st.text_input("الرمز السري Secret:", value=b_sec, type="password")
        autoEn = st.checkbox("تفعيل محرك التنفيذ الآلي الذكي", value=bool(b_en))
        if st.form_submit_button("حفظ إعدادات الروبوت"):
            conn = sqlite3.connect('apex_quant.db', check_same_thread=False)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO bot_settings(username, api_key, api_secret, auto_trade_enabled) VALUES (?, ?, ?, ?)', 
                      (st.session_state['username'], apiKey, apiSec, 1 if autoEn else 0))
            conn.commit()
            conn.close()
            st.success("تم الحفظ بنجاح!")

elif app_mode == "سجل الصفقات الحي والأداء (Trade Journal & PnL)":
    st.title("📈 سجل الصفقات ومنحنى الأداء الحي (Equity Curve)")
    st.caption("متابعة حية لعوائد الصفقات المسجلة وتقييم الأداء العام.")
    st.markdown("---")
    
    trades_df = get_trade_journal(st.session_state['username'])
    if not trades_df.empty:
        st.subheader("📋 جدول الصفقات المسجلة")
        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("لا توجد صفقات مسجلة حتى الآن. يمكنك تسجيل صفقات من خلال لوحة التحليل الفردي.")

elif app_mode == "ماسح السوق الشامل (Market Screener)":
    st.title("🗺️ ماسح السوق الشامل للفرص الاستثمارية")
    st.caption("فحص ذكي ومتعدد الأصول لاستخراج أقوى الإشارات لحظياً.")
    st.markdown("---")
    
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
                        Xt = cl_t[advanced_features]
                        yt = (cl_t['Close'].shift(-1) > cl_t['Close']).astype(int)
                        vt = yt.dropna().index
                        
                        xgb_t = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.02, random_state=42)
                        rf_t = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
                        xgb_t.fit(Xt.loc[vt], yt.loc[vt])
                        rf_t.fit(Xt.loc[vt], yt.loc[vt])
                        
                        p1 = xgb_t.predict_proba(Xt.iloc[-1:])[0]
                        p2 = rf_t.predict_proba(Xt.iloc[-1:])[0]
                        avg_p = (p1 + p2) / 2.0
                        
                        pred_val = 1 if avg_p[1] > avg_p[0] else 0
                        max_conf = max(avg_p)
                        adx_v = float(df_temp['ADX'].iloc[-1])
                        px_v = float(df_temp['Close'].iloc[-1])
                        
                        dec = "📈 شراء" if pred_val == 1 and max_conf >= conf_threshold_input else ("📉 بيع" if pred_val == 0 and max_conf >= conf_threshold_input else "⚠️ ترقب")
                        res.append({
                            "الأصل": ast,
                            "السعر": f"${px_v:,.2f}",
                            "قوة الاتجاه ADX": f"{adx_v:.1f}",
                            "قرار النظام": dec,
                            "الثقة": f"{max_conf*100:.1f}%"
                        })
        if res:
            st.table(pd.DataFrame(res))
        else:
            st.warning("لم يتم العثور على بيانات كافية.")

elif app_mode == "مصفوفة مقارنة الأسواق والـ MPT":
    st.title("📊 مصفوفة ارتباط الأصول والتحسين الحديث للمحافظ")
    st.caption("توزيع الأوزان الأمثل بناءً على نموذج ماركويتز ونسبة شارب.")
    st.markdown("---")
    
    default_w = ["BTC-USD", "GC=F", "EURUSD=X", "AAPL"]
    w_input = st.text_input("أصول المقارنة:", value=", ".join(default_w))
    w_assets = [x.strip().upper() for x in w_input.split(',')]
    
    price_dict = {}
    for ast in w_assets:
        df_a = load_and_process_data(ast)
        if df_a is not None and not df_a.empty:
            price_dict[ast] = df_a['Close']
            
    if len(price_dict) > 1:
        pdf = pd.DataFrame(price_dict).dropna()
        rets = pdf.pct_change().dropna()
        
        st.subheader("🔗 مصفوفة الارتباط (Correlation Matrix)")
        st.plotly_chart(px.imshow(rets.corr(), text_auto=True, color_continuous_scale="RdBu_r", aspect="auto"), use_container_width=True)
        
        st.subheader("⚖️ الأوزان المثالية حسب نموذج شارب")
        mean_r = rets.mean()
        cov_r = rets.cov()
        num_a = len(rets.columns)
        
        np.random.seed(42)
        best_s = -999
        best_w = np.ones(num_a) / num_a
        for _ in range(5000):
            w = np.random.random(num_a)
            w /= np.sum(w)
            ret_val = np.dot(w, mean_r) * 252
            vol_val = np.sqrt(np.dot(w.T, np.dot(cov_r * 252, w)))
            sharpe = ret_val / (vol_val + 1e-9)
            if sharpe > best_s:
                best_s = sharpe
                best_w = w
                
        st.table(pd.DataFrame({"الأصل": rets.columns, "الوزن المقترح (%)": (best_w * 100).round(2)}))

else:
    with st.spinner(f"جاري معالجة بيانات الأصل '{crypto_symbol}' بالذكاء الاصطناعي..."):
        data = load_and_process_data(crypto_symbol, rsi_window=rsi_period_input)

    if data is None or data.empty:
        st.error(f"⚠️ عذراً، تعذر جلب البيانات للرمز '{crypto_symbol}'.")
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
        st.caption("النسخة الفريدة الشاملة: أهداف ديناميكية، تحليل مشاعر، سجل صفقات، ودعم كافة الأسواق.")
        st.markdown("---")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("السعر الحالي", f"${current_price:,.2f}")
        with c2:
            st.metric("حالة المشاعر", news_sentiment)
        with c3:
            st.metric("قوة الاتجاه ADX", f"{current_adx:.1f}")
        with c4:
            dec_str = "📈 شراء" if prediction == 1 and max_prob >= conf_threshold_input else ("📉 بيع" if prediction == 0 and max_prob >= conf_threshold_input else "⚠️ ترقب")
            st.metric("قرار النظام المستقل", dec_str, delta=f"الثقة: {max_prob*100:.1f}%")

        st.markdown("---")
        st.subheader("🎯 مصفوفة الأهداف الديناميكية ووقف الخسارة")
        t1, t2, t3, t4, t5 = st.columns(5)
        with t1:
            st.metric("وقف الخسارة", f"${sl_price:,.2f}")
        with t2:
            st.metric("الهدف الأول TP1", f"${tp1_price:,.2f}")
        with t3:
            st.metric("الهدف الثاني TP2", f"${tp2_price:,.2f}")
        with t4:
            st.metric("الهدف الثالث TP3", f"${tp3_price:,.2f}")
        with t5:
            st.metric("نشاط الحيتان", f"{current_spike:.2f}x")

        # زر تسجيل الصفقة
        if st.button("📝 تسجيل هذه الصفقة في السجل الحي"):
            log_trade(st.session_state['username'], crypto_symbol, dec_str, current_price, 1.0)
            st.success("تم تسجيل الصفقة بنجاح في سجلك السحابي!")

        st.markdown("---")
        st.subheader("📈 الرسم البياني التفاعلي")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='السعر', line=dict(color='#00FFA3', width=2)))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

        # مولد التقارير الاحترافية كملف نصي/HTML قابل للتحميل الفوري
        st.markdown("---")
        st.subheader("📑 تقرير التحليل المؤسسي القابل للتصدير")
        report_content = f"""
        === APEX QUANT INSTITUTIONAL REPORT ===
        Symbol: {crypto_symbol}
        Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
        Current Price: ${current_price:,.2f}
        System Decision: {dec_str} (Confidence: {max_prob*100:.1f}%)
        Stop Loss: ${sl_price:,.2f}
        Take Profit 1: ${tp1_price:,.2f}
        Take Profit 2: ${tp2_price:,.2f}
        Take Profit 3: ${tp3_price:,.2f}
        Market Sentiment: {news_sentiment}
        ========================================
        """
        st.download_button(
            label="📥 تحميل التقرير المؤسسي (TXT Report)",
            data=report_content,
            file_name=f"{crypto_symbol}_Apex_Report.txt",
            mime="text/plain"
        )
