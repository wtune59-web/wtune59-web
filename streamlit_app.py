import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier
import xml.etree.ElementTree as ET
import sqlite3
import hashlib

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant SaaS Platform - Institutional Edition",
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
st.sidebar.title("⚡ لوحة التحكم المؤسسية")

app_mode = st.sidebar.radio("🧭 وضع المنصة:", ["تحليل فردي معمق", "مصفوفة مقارنة الأصول (Multi-Asset)"])

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

st.sidebar.markdown("---")
st.sidebar.header("💡 شراكات المنصات")
st.sidebar.markdown("[🔗 سجل في Binance واحصل على خصم](https://accounts.binance.com/register?ref=YOUR_REF_ID)")


# --- دوال جلب البيانات العالمية والمؤسسية ---
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
def load_and_process_data(symbol):
    try:
        data = yf.download(symbol, period='1y', progress=False)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        data = data.reset_index()
        data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
        
        # دمج مؤشر الخوف والجشع
        fng_df = get_fear_and_greed()
        if fng_df is not None:
            data = pd.merge(data, fng_df, on='Date', how='left')
            data['Fear_Greed_Index'] = data['Fear_Greed_Index'].fillna(50)
        else:
            data['Fear_Greed_Index'] = 50

        # دمج مؤشر التقلب العالمي VIX
        vix_df = get_vix_data()
        if vix_df is not None:
            data = pd.merge(data, vix_df, on='Date', how='left')
            data['VIX'] = data['VIX'].fillna(20.0)
        else:
            data['VIX'] = 20.0
            
        data.set_index('Date', inplace=True)
        
        # الهندسة الرياضية والمؤشرات المتقدمة لرفع دقة التوقع
        data['Price_Change'] = data['Close'].pct_change()
        data['Volume_Change'] = data['Volume'].pct_change()
        data['Lag_1'] = data['Price_Change'].shift(1)
        data['Lag_2'] = data['Price_Change'].shift(2)
        data['Lag_3'] = data['Price_Change'].shift(3)
        
        data['SMA_10'] = data['Close'].rolling(10).mean()
        data['SMA_30'] = data['Close'].rolling(30).mean()
        data['SMA_Ratio'] = data['SMA_10'] / data['SMA_30']
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR (Average True Range) لقياس تقلبات السوق والخطورة
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        data['ATR'] = true_range.rolling(14).mean() / data['Close']
        
        # Stochastic Oscillator لقياس الزخم
        low_14 = data['Low'].rolling(14).min()
        high_14 = data['High'].rolling(14).max()
        data['Stochastic_K'] = 100 * (data['Close'] - low_14) / (high_14 - low_14 + 1e-9)
        
        # Volume Liquidity Ratio
        data['Vol_Ratio'] = data['Volume'] / (data['Volume'].rolling(20).mean() + 1e-9)
        
        # Bollinger Bands
        data['BB_Middle'] = data['Close'].rolling(20).mean()
        data['BB_Std'] = data['Close'].rolling(20).std()
        data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
        data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
        data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Middle']
        
        # MACD
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


# قائمة الميزات المتقدمة الشاملة للنموذج المؤسسي
advanced_features = [
    'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2', 'Lag_3',
    'SMA_Ratio', 'RSI', 'ATR', 'Stochastic_K', 'Vol_Ratio', 
    'Fear_Greed_Index', 'VIX', 'BB_Width', 'MACD', 'MACD_Signal'
]


@st.cache_data(ttl=3600)
def analyze_asset_fast(asset):
    df_asset = load_and_process_data(asset)
    if df_asset is not None and not df_asset.empty:
        clean = df_asset.dropna()
        if len(clean) > 20:
            X_c = clean[advanced_features]
            y_c = (clean['Close'].shift(-1) > clean['Close']).astype(int)
            valid = y_c.dropna().index
            
            model_c = XGBClassifier(n_estimators=70, max_depth=3, learning_rate=0.03, random_state=42)
            model_c.fit(X_c.loc[valid], y_c.loc[valid])
            
            pred_c = model_c.predict(X_c.iloc[-1:])[0]
            prob_c = model_c.predict_proba(X_c.iloc[-1:])[0]
            max_p = max(prob_c)
            
            decision = "📈 شراء (صعود)" if pred_c == 1 and max_p >= 0.58 else ("📉 بيع / تجنب" if pred_c == 0 and max_p >= 0.58 else "⚠️ ترقب (حياد)")
            
            return {
                "الأصل": asset,
                "السعر الحالي ($)": f"${float(df_asset['Close'].iloc[-1]):,.2f}",
                "مؤشر RSI": f"{float(df_asset['RSI'].iloc[-1]):.1f}",
                "مؤشر ATR": f"{float(df_asset['ATR'].iloc[-1])*100:.2f}%",
                "قرار النظام": decision,
                "نسبة الثقة": f"{max_p*100:.1f}%"
            }
    return None


if app_mode == "مصفوفة مقارنة الأصول (Multi-Asset)":
    st.title("📊 مصفوفة المقارنة المؤسسية متعددة الأصول")
    st.caption("تحليل مدعوم بمؤشرات الـ VIX العالمية والتقلبات المتقدمة ATR و Stochastic.")
    st.markdown("---")
    
    default_watchlist = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AAPL", "TSLA"]
    watchlist_input = st.text_input("أدخل الأصول مفصولة بفواصل:", value=", ".join(default_watchlist))
    assets = [a.strip().upper() for a in watchlist_input.split(',')]
    
    comparison_data = []
    with st.spinner("جاري تشغيل محرك الذكاء الاصطناعي المؤسسي..."):
        for asset in assets:
            res = analyze_asset_fast(asset)
            if res:
                comparison_data.append(res)
                
    if comparison_data:
        st.table(pd.DataFrame(comparison_data))
    else:
        st.warning("لم يتم العثور على بيانات كافية للأصول المدخلة.")

else:
    with st.spinner(f"جاري معالجة التحليل المؤسسي لـ {crypto_symbol}..."):
        data = load_and_process_data(crypto_symbol)
        sentiment_label, news_headlines = get_news_sentiment(crypto_symbol)

    if data is None or data.empty:
        st.error(f"⚠️ عذراً، لم يتم العثور على بيانات للرمز '{crypto_symbol}'. تحقق من الرمز.")
    else:
        clean_data = data.dropna()
        X = clean_data[advanced_features]
        y = (clean_data['Close'].shift(-1) > clean_data['Close']).astype(int)
        
        valid_idx = y.dropna().index
        model = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.015, subsample=0.8, colsample_bytree=0.8, random_state=42)
        model.fit(X.loc[valid_idx], y.loc[valid_idx])

        today_features = data[advanced_features].iloc[-1:]
        prediction = model.predict(today_features)[0]
        probabilities = model.predict_proba(today_features)[0]

        current_price = float(data['Close'].iloc[-1])
        current_fng = int(data['Fear_Greed_Index'].iloc[-1])
        current_vix = float(data['VIX'].iloc[-1])
        current_rsi = float(data['RSI'].iloc[-1])
        current_atr = float(data['ATR'].iloc[-1]) * 100
        max_prob = max(probabilities)
        confidence_threshold = 0.58

        st.title(f"🧠 منصة التحليل المعرفي المؤسسي لـ {crypto_symbol}")
        st.caption("مدعوم بنماذج XGBoost مع محركات VIX والتقلبات المتقدمة.")
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")
        with col2:
            st.metric(label="📉 تقلب السوق (VIX)", value=f"{current_vix:.1f}")
        with col3:
            st.metric(label="😨 الخوف والجشع", value=f"{current_fng} / 100")
        with col4:
            if max_prob < confidence_threshold:
                st.metric(label="🔮 قرار النظام", value="⚠️ حياد (ترقب)", delta=f"الثقة: {max_prob*100:.1f}%")
            elif prediction == 1:
                st.metric(label="🔮 قرار النظام", value="📈 شراء (صعود)", delta=f"الثقة: {max_prob*100:.1f}%")
            else:
                st.metric(label="🔮 قرار النظام", value="📉 بيع / تجنب", delta=f"الثقة: {max_prob*100:.1f}%", delta_color="inverse")

        st.markdown("---")
        st.subheader("📝 التقرير الاستشاري التفسيري المؤسسي")
        st.markdown(f"""
        > * **التقلبات والمخاطر (ATR):** معدل التحرك المتوقع للأصل يقدر بـ **{current_atr:.2f}%**، مما يساعد في قياس مستويات المخاطرة الحالية بدقة.
        > * **المؤشرات الفنية والزخم:** مؤشر القوة النسبية RSI يسجل **{current_rsi:.1f}**، مع تقييم مؤشر الخوف والجشع العام **{current_fng}/100** ومؤشر التقلب العالمي VIX بقيمة **{current_vix:.1f}**.
        > * **الخلاصة المؤسسية:** بلغت نسبة ثقة نموذج الـ XGBoost المعزز بـ 15 مؤشراً فرعياً **{max_prob*100:.1f}%**، والقرار المعتمد للمحفظة هو: **{"شراء" if prediction == 1 and max_prob >= confidence_threshold else ("بيع" if prediction == 0 and max_prob >= confidence_threshold else "ترقب وحياد")}**.
        """)

        st.markdown("---")
        st.subheader("💼 أداء محفظتك السحابية للأصل الحالي")
        if portfolio_qty > 0:
            val = portfolio_qty * current_price
            invested = portfolio_qty * portfolio_buy_price
            pnl_d = val - invested
            pnl_p = (pnl_d / invested) * 100 if invested > 0 else 0
            
            p1, p2, p3 = st.columns(3)
            with p1:
                st.metric(label="قيمة أصولك السحابية", value=f"${val:,.2f}")
            with p2:
                st.metric(label="رأس المال المستثمر", value=f"${invested:,.2f}")
            with p3:
                st.metric(label="الأرباح / الخسائر (PnL)", value=f"${pnl_d:,.2f}", delta=f"{pnl_p:.2f}%")
        else:
            st.info("أدخل كمية وسعر الشراء في الشريط الجانبي واضغط 'حفظ تعديلات المحفظة' لتتبع أرباحك لحظياً.")

        st.markdown("---")
        st.subheader("🧪 محرك الاختبار العكسي التاريخي (Backtest Performance)")
        clean_data['Model_Pred'] = model.predict(X)
        clean_data['Strategy_Return'] = clean_data['Model_Pred'].shift(1) * clean_data['Price_Change']
        strategy_cum = (1 + clean_data['Strategy_Return'].fillna(0)).cumprod() - 1
        buyhold_cum = (1 + clean_data['Price_Change']).cumprod() - 1
        
        backtest_df = pd.DataFrame({
            'استراتيجية النظام المعرفي (%)': strategy_cum * 100,
            'الشراء والاحتفاظ التقليدي (%)': buyhold_cum * 100
        }, index=clean_data.index)
        st.line_chart(backtest_df)

        st.markdown("---")
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            st.subheader(f"📊 مؤشرات التحليل الفني لـ {crypto_symbol}")
            tab1, tab2, tab3 = st.tabs(["📉 السعر والبولنجر باند", "📈 مؤشر الزخم Stochastic", "⚡ مؤشر العزم (MACD)"])
            with tab1:
                st.line_chart(data[['Close', 'BB_Upper', 'BB_Lower']])
            with tab2:
                st.line_chart(data['Stochastic_K'])
            with tab3:
                st.line_chart(data[['MACD', 'MACD_Signal']])
        with col_g2:
            st.subheader("📰 أحدث الأخبار الإخبارية")
            for headline in news_headlines:
                st.markdown(f"- {headline}")
