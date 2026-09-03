import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Global Quant & AI Trading Platform",
    page_icon="🌍",
    layout="wide"
)

# 1. الشريط الجانبي للإعدادات والبحث الحر ومتتبع المحفظة
st.sidebar.title("🌍 لوحة التحكم العالمية")
st.sidebar.markdown("---")

# ميزة البحث الحر عن أي أصل عالمي (عملات رقمية، أسهم، إلخ)
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
st.title("🌐 منصة التحليل الكمي العالمي والذكاء الاصطناعي")
st.caption("نظام مؤسسي متكامل يضم: توقعات XGBoost، اختبارات عكسية تاريخية، وإدارة المحافظ اللحظية.")
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

# جلب بيانات الأصل ومعالجة المؤشرات الذكية
@st.cache_data(ttl=1800)
def load_and_process_global_data(symbol):
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
            data['Fear_Greed_Index'] = data['Fear_Greed_Index'].fillna(50) # قيمة افتراضية في حال الأسهم التقليدية
        else:
            data['Fear_Greed_Index'] = 50
            
        data.set_index('Date', inplace=True)
        
        # هندسة الميزات المتقدمة
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

with st.spinner(f"جاري جلب بيانات الأصل وتحليل السوق لـ {crypto_symbol}..."):
    data = load_and_process_global_data(crypto_symbol)

if data is None or data.empty:
    st.error(f"⚠️ عذراً، لم يتم العثور على بيانات للرمز '{crypto_symbol}'. تأكد من كتابة الرمز بشكل صحيح (مثل BTC-USD أو TSLA).")
else:
    features = [
        'Price_Change', 'Volume_Change', 'Lag_1', 'Lag_2', 'Lag_3',
        'SMA_Ratio', 'RSI', 'Fear_Greed_Index', 'BB_Width', 'MACD', 'MACD_Signal'
    ]

    clean_data = data.dropna()
    X = clean_data[features]
    y = (clean_data['Close'].shift(-1) > clean_data['Close']).astype(int)
    
    # محاذاة البيانات للتدريب
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
    max_prob = max(probabilities)
    confidence_threshold = 0.58

    # --- القسم الأول: مؤشرات التوقع والذكاء الاصطناعي ---
    st.subheader("🎯 توصية الذكاء الاصطناعي وإدارة المخاطر")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")
    with col2:
        st.metric(label="😨 مؤشر السوق / الفنغ", value=f"{current_fng} / 100")
    with col3:
        if max_prob < confidence_threshold:
            st.metric(label="🔮 قرار النظام العالمي", value="⚠️ ترقب (سوق غير واضح)", delta=f"الثقة: {max_prob*100:.1f}%")
        elif prediction == 1:
            st.metric(label="🔮 قرار النظام العالمي", value="📈 شراء (صعود متوقع)", delta=f"الثقة: {max_prob*100:.1f}%")
        else:
            st.metric(label="🔮 قرار النظام العالمي", value="📉 بيع / تجنب (هبوط)", delta=f"الثقة: {max_prob*100:.1f}%", delta_color="inverse")

    # --- القسم الثاني: متتبع المحفظة الشخصية (Portfolio PnL) ---
    st.markdown("---")
    st.subheader("💼 أداء محفظتك اللحظي للأصل الحالي")
    if portfolio_qty > 0:
        current_portfolio_value = portfolio_qty * current_price
        invested_amount = portfolio_qty * portfolio_buy_price
        pnl_dollar = current_portfolio_value - invested_amount
        pnl_percent = (pnl_dollar / invested_amount) * 100 if invested_amount > 0 else 0
        
        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric(label="إجمالي قيمة الأصول", value=f"${current_portfolio_value:,.2f}")
        with p2:
            st.metric(label="إجمالي رأس المال المستثمر", value=f"${invested_amount:,.2f}")
        with p3:
            st.metric(label="الربح / الخسارة (PnL)", value=f"${pnl_dollar:,.2f}", delta=f"{pnl_percent:.2f}%")
    else:
        st.info("قم بإدخال الكمية وسعر الشراء في الشريط الجانبي لمتابعة أرباحك وخسائرك.")

    # --- القسم الثالث: محرك الاختبار العكسي للاستراتيجية (Backtesting Engine) ---
    st.markdown("---")
    st.subheader("🧪 محرك الاختبار العكسي التاريخي (Backtest Performance)")
    st.caption("مقارنة العائد التاريخي لاستراتيجية الذكاء الاصطناعي مقابل الشراء والاحتفاظ التقليدي خلال الفترة السابقة.")
    
    clean_data['Model_Pred'] = model.predict(X)
    clean_data['Strategy_Return'] = clean_data['Model_Pred'].shift(1) * clean_data['Price_Change']
    
    # حساب العائد التراكمي
    strategy_cum = (1 + clean_data['Strategy_Return'].fillna(0)).cumprod() - 1
    buyhold_cum = (1 + clean_data['Price_Change']).cumprod() - 1
    
    backtest_df = pd.DataFrame({
        'استراتيجية الذكاء الاصطناعي (%)': strategy_cum * 100,
        'الشراء والاحتفاظ التقليدي (%)': buyhold_cum * 100
    }, index=clean_data.index)
    
    st.line_chart(backtest_df)

    # --- القسم الرابع: الرسوم البيانية التقنية ---
    st.markdown("---")
    st.subheader(f"📊 مؤشرات التحليل الفني المتقدمة لـ {crypto_symbol}")
    tab1, tab2, tab3 = st.tabs(["📉 السعر والبولنجر باند", "📈 مؤشر القوة النسبية (RSI)", "⚡ مؤشر العزم (MACD)"])

    with tab1:
        st.line_chart(data[['Close', 'BB_Upper', 'BB_Lower']])
    with tab2:
        st.line_chart(data['RSI'])
    with tab3:
        st.line_chart(data[['MACD', 'MACD_Signal']])
