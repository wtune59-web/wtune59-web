import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from xgboost import XGBClassifier

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Advanced Crypto AI Intelligence",
    page_icon="🚀",
    layout="wide"
)

# 1. الشريط الجانبي للإعدادات وروابط الإحالة
st.sidebar.title("لوحة التحكم المتقدمة")
st.sidebar.markdown("---")

crypto_symbol = st.sidebar.selectbox(
    "📊 اختر العملة الرقمية:",
    ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD"]
)

st.sidebar.markdown("---")
st.sidebar.header("💡 انضم إلى منصات التداول")
st.sidebar.markdown("[🔗 سجل في Binance واحصل على خصم](https://accounts.binance.com/register?ref=YOUR_REF_ID)")
st.sidebar.markdown("[🔗 سجل في Bybit لتداول العملات](https://www.bybit.com/invite?ref=YOUR_REF_ID)")

# 2. الواجهة الرئيسية
st.title("📈 منصة التحليل الفني والذكاء الاصطناعي المتقدمة")
st.caption("نظام هجين يدمج خوارزميات XGBoost المتطورة، مؤشرات الزخم المتقدمة، ومؤشر الخوف والجشع.")
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

# جلب بيانات العملة ومعالجة المؤشرات الموسعة
@st.cache_data(ttl=1800)
def load_and_process_advanced_data(symbol):
    data = yf.download(symbol, period='3y', progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    data = data.reset_index()
    data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
    
    fng_df = get_fear_and_greed()
    if fng_df is not None:
        data = pd.merge(data, fng_df, on='Date', how='inner')
        
    data.set_index('Date', inplace=True)
    
    # --- توسيع التحليلات ومؤشرات الذكاء الاصطناعي ---
    data['Price_Change'] = data['Close'].pct_change()
    data['Volume_Change'] = data['Volume'].pct_change()
    
    # المتوسطات المتحركة
    data['SMA_10'] = data['Close'].rolling(10).mean()
    data['SMA_30'] = data['Close'].rolling(30).mean()
    data['SMA_Ratio'] = data['SMA_10'] / data['SMA_30']
    
    # مؤشر القوة النسبية (RSI)
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # مؤشر البولنجر باند (Bollinger Bands)
    data['BB_Middle'] = data['Close'].rolling(20).mean()
    data['BB_Std'] = data['Close'].rolling(20).std()
    data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
    data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
    data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Middle']
    
    # مؤشر الماكد (MACD)
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
    
    return data

with st.spinner(f"جاري تشغيل محرك التحليل المتقدم وتحليل بيانات {crypto_symbol}..."):
    data = load_and_process_advanced_data(crypto_symbol)
    
    # قائمة العوامل الموسعة للذكاء الاصطناعي
    features = [
        'Price_Change', 'Volume_Change', 'SMA_Ratio', 'RSI', 
        'Fear_Greed_Index', 'BB_Width', 'MACD', 'MACD_Signal'
    ]

    today_features = data[features].iloc[-1:]
    data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    clean_data = data.dropna()

    X = clean_data[features]
    y = clean_data['Target']

    # تدريب نموذج متقدم بـ 150 شجرة قرار لزيادة الدقة
    model = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.02, random_state=42)
    model.fit(X, y)

    prediction = model.predict(today_features)[0]
    probabilities = model.predict_proba(today_features)[0]

# --- عرض النتائج المتقدمة في كروت ---
current_price = float(data['Close'].iloc[-1])
current_fng = int(data['Fear_Greed_Index'].iloc[-1]) if 'Fear_Greed_Index' in data.columns else "N/A"
current_rsi = float(data['RSI'].iloc[-1]) if 'RSI' in data.columns else 0

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")

with col2:
    st.metric(label="😨 مؤشر الخوف والجشع", value=f"{current_fng} / 100")

with col3:
    if prediction == 1:
        st.metric(label="🔮 توقع حركة الغد (متقدم)", value="📈 ارتفاع متوقع", delta=f"ثقة النظام: {probabilities[1]*100:.1f}%")
    else:
        st.metric(label="🔮 توقع حركة الغد (متقدم)", value="📉 انخفاض متوقع", delta=f"ثقة النظام: {probabilities[0]*100:.1f}%", delta_color="inverse")

st.markdown("---")

# --- الرسوم البيانية المتعددة ---
st.subheader(f"📊 مؤشرات التحليل العميق لـ {crypto_symbol}")
tab1, tab2, tab3 = st.tabs(["📉 السعر والبولنجر باند", "📈 مؤشر القوة النسبية (RSI)", "⚡ مؤشر العزم (MACD)"])

with tab1:
    st.line_chart(data[['Close', 'BB_Upper', 'BB_Lower']])

with tab2:
    st.line_chart(data['RSI'])

with tab3:
    st.line_chart(data[['MACD', 'MACD_Signal']])
