import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier
import xml.etree.ElementTree as ET

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Cognitive Global Quant Platform",
    page_icon="🧠",
    layout="wide"
)

# 1. الشريط الجانبي للإعدادات والبحث ومحفظة الأصول
st.sidebar.title("🧠 لوحة التحكم المعرفية")
st.sidebar.markdown("---")

user_symbol_input = st.sidebar.text_input("🔍 أدخل رمز الأصل (مثال: BTC-USD, ETH-USD, AAPL):", value="BTC-USD")
crypto_symbol = user_symbol_input.strip().upper()

st.sidebar.markdown("---")
st.sidebar.header("💼 محفظتي الشخصية (Portfolio)")
portfolio_qty = st.sidebar.number_input("الكمية المملوكة:", min_value=0.0, value=0.1, step=0.01)
portfolio_buy_price = st.sidebar.number_input("متوسط سعر الشراء ($):", min_value=0.0, value=60000.0, step=100.0)

st.sidebar.markdown("---")
st.sidebar.header("💡 شراكات المنصات")
st.sidebar.markdown("[🔗 سجل في Binance واحصل على خصم](https://accounts.binance.com/register?ref=YOUR_REF_ID)")
st.sidebar.markdown("[🔗 سجل في Bybit لتداول العملات](https://www.bybit.com/invite?ref=YOUR_REF_ID)")

# 2. الواجهة الرئيسية
st.title("🧠 المنصة الكمية المعرفية المدعومة بالذكاء الاصطناعي التفسيري")
st.caption("نظام هجين يدمج: تنبؤات XGBoost، التحليل اللفظي التفسيري، قياس مشاعر الأخبار الحية، والاختبارات العكسية.")
st.markdown("---")

# دالة جلب مؤشر الخوف والجشع
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

# دالة جلب وتحليل مشاعر الأخبار الاقتصادية عبر RSS خفيف
@st.cache_data(ttl=1800)
def get_news_sentiment(symbol):
    try:
        # استخدام ياهو فاينانس للأخبار RSS الخاصة بالرمز
        ticker_base = symbol.split('-')[0]
        rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker_base}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(rss_url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            titles = [elem.text for elem in root.iter('title') if elem.text]
            
            # كلمات مفتاحية بسيطة لتقدير المشاعر
            positive_words = ['surge', 'jump', 'gain', 'bull', 'rally', 'high', 'growth', 'up', 'ارتفاع', 'صعود']
            negative_words = ['drop', 'fall', 'crash', 'bear', 'loss', 'down', 'risk', 'dip', 'هبوط', 'انخفاض']
            
            score = 0
            count = 0
            for title in titles[:10]: # فحص أحدث 10 عناوين
                t_lower = title.lower()
                for p in positive_words:
                    if p in t_lower: score += 1
                for n in negative_words:
                    if n in t_lower: score -= 1
                count += 1
                
            if score > 0: return "إيجابي 🟢", titles[:3]
            elif score < 0: return "سلبي 🔴", titles[:3]
        return "محايد ⚪", ["لا توجد أخبار بارزة حديثة."]
    except:
        return "محايد ⚪", ["تعذر جلب الأخبار الحية."]

# جلب البيانات ومعالجة المؤشرات
@st.cache_data(ttl=1800)
def load_and_process_cognitive_data(symbol):
    try:
        data = yf.download(symbol, period='3y', progress=False)
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
            
        data.set_index('Date', inplace=True)
        
        data['Price_Change'] = data['Close'].pct_change()
        data['Volume_Change'] = data['Volume'].pct_change()
        data['Lag_1'] = data['Price_Change'].shift(1)
        data['Lag_2'] = data['Price_Change'].shift(2)
        data['Lag_3'] = data['Price_Change'].shift(3)
        
        data['SMA_10'] = data['Close'].rolling(10).mean()
        data['SMA_30'] = data['Close'].rolling(30).mean()
        data['SMA_Ratio'] = data['SMA_10'] / data['SMA_30']
        
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        data['BB_Middle'] = data['Close'].rolling(20).mean()
        data['BB_Std'] = data['Close'].rolling(20).std()
        data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
        data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
        data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Middle']
        
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        
        return data
    except Exception as e:
        return None

with st.spinner(f"جاري تشغيل محرك التحليل المعرفي لـ {crypto_symbol}..."):
    data = load_and_process_cognitive_data(symbol=crypto_symbol)
    sentiment_label, news_headlines = get_news_sentiment(crypto_symbol)

if data is None or data.empty:
    st.error(f"⚠️ عذراً، لم يتم العثور على بيانات للرمز '{crypto_symbol}'. يرجى التحقق من صحة الرمز.")
else:
    features = [
        'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2', 'Lag_3',
        'SMA_Ratio', 'RSI', 'Fear_Greed_Index', 'BB_Width', 'MACD', 'MACD_Signal'
    ]

    clean_data = data.dropna()
    X = clean_data[features]
    y = (clean_data['Close'].shift(-1) > clean_data['Close']).astype(int)
    
    valid_idx = y.dropna().index
    X_train = X.loc[valid_idx]
    y_train = y.loc[valid_idx]

    model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.015, subsample=0.8, colsample_bytree=0.8, random_state=42)
    model.fit(X_train, y_train)

    today_features = data[features].iloc[-1:]
    prediction = model.predict(today_features)[0]
    probabilities = model.predict_proba(today_features)[0]

    current_price = float(data['Close'].iloc[-1])
    current_fng = int(data['Fear_Greed_Index'].iloc[-1])
    current_rsi = float(data['RSI'].iloc[-1])
    max_prob = max(probabilities)
    confidence_threshold = 0.58

    # --- 1. قسم التوصية الذكية المعرفية ---
    st.subheader("🎯 التوصية المعرفية وإدارة المخاطر التكيفية")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")
    with col2:
        st.metric(label="📰 مشاعر الأخبار الحية", value=sentiment_label)
    with col3:
        st.metric(label="😨 مؤشر الخوف والجشع", value=f"{current_fng} / 100")
    with col4:
        if max_prob < confidence_threshold:
            st.metric(label="🔮 قرار النظام المعرفي", value="⚠️ حياد (ترقب)", delta=f"الثقة: {max_prob*100:.1f}%")
        elif prediction == 1:
            st.metric(label="🔮 قرار النظام المعرفي", value="📈 شراء (صعود)", delta=f"الثقة: {max_prob*100:.1f}%")
        else:
            st.metric(label="🔮 قرار النظام المعرفي", value="📉 بيع / تجنب", delta=f"الثقة: {max_prob*100:.1f}%", delta_color="inverse")

    # --- 2. التقرير الاستشاري التفسيري (LLM Explanation Layer) ---
    st.markdown("---")
    st.subheader("📝 التقرير الاستشاري التفسيري للذكاء الاصطناعي")
    
    # توليد نص تحليلي منطقي بناءً على المؤشرات
    rsi_status = "في مناطق التشبع البيعي (فرصة مرتدة محتملة)" if current_rsi < 35 else ("في مناطق التشبع الشرايي (حذر مطلوب)" if current_rsi > 65 else "في مستويات متوازنة ومستقرة")
    trend_status = "صاعد ومتماسك" if current_price > float(data['SMA_30'].iloc[-1]) else "هابط أو تحت الضغط"
    
    explanation_text = f"""
    > **تحليل الحالة للأصل `{crypto_symbol}`:**
    > * **حركة السعر والاتجاه:** الاتجاه المتوسط للأصل يعتبر **{trend_status}**، بينما يسجل مؤشر القوة النسبية (RSI) قيمة **{current_rsi:.1f}** مما يجعله **{rsi_status}**.
    > * **حالة السوق العامة:** مؤشر الخوف والجشع يسجل **{current_fng}/100**، وحالة مشاعر الأخبار الحية تميل إلى كونها **{sentiment_label}**.
    > * **الخلاصة التفسيرية:** بناءً على تقاطع الذاكرة السعرية مع الزخم (MACD) ونطاقات البولنجر، قدر نموذج الـ XGBoost نسبة الثقة عند **{max_prob*100:.1f}%**. بناءً على قواعد إدارة المخاطر، تم تصنيف القرار كـ **{"شراء" if prediction == 1 and max_prob >= confidence_threshold else ("بيع" if prediction == 0 and max_prob >= confidence_threshold else "حالة حياد وترقب")}**.
    """
    st.markdown(explanation_text)

    # --- 3. محفظة الأصول والربح/الخسارة ---
    st.markdown("---")
    st.subheader("💼 أداء محفظتك اللحظي")
    if portfolio_qty > 0:
        current_portfolio_value = portfolio_qty * current_price
        invested_amount = portfolio_qty * portfolio_buy_price
        pnl_dollar = current_portfolio_value - invested_amount
        pnl_percent = (pnl_dollar / invested_amount) * 100 if invested_amount > 0 else 0
        
        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric(label="إجمالي قيمة الأصول", value=f"${current_portfolio_value:,.2f}")
        with p2:
            st.metric(label="رأس المال المستثمر", value=f"${invested_amount:,.2f}")
        with p3:
            st.metric(label="الربح / الخسارة (PnL)", value=f"${pnl_dollar:,.2f}", delta=f"{pnl_percent:.2f}%")
    else:
        st.info("أدخل الكمية وسعر الشراء في الشريط الجانبي لمتابعة أرباح محفظتك.")

    # --- 4. الاختبار العكسي للاستراتيجية (Backtesting) ---
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

    # --- 5. الرسوم البيانية الفنية والأخبار المرفقة ---
    st.markdown("---")
    col_g1, col_g2 = st.columns([2, 1])
    
    with col_g1:
        st.subheader(f"📊 مؤشرات التحليل الفني لـ {crypto_symbol}")
        tab1, tab2, tab3 = st.tabs(["📉 السعر والبولنجر باند", "📈 مؤشر القوة النسبية (RSI)", "⚡ مؤشر العزم (MACD)"])
        with tab1:
            st.line_chart(data[['Close', 'BB_Upper', 'BB_Lower']])
        with tab2:
            st.line_chart(data['RSI'])
        with tab3:
            st.line_chart(data[['MACD', 'MACD_Signal']])
            
    with col_g2:
        st.subheader("📰 أبرز العناوين الإخبارية الحية")
        for headline in news_headlines:
            st.markdown(f"- {headline}")
