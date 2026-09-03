import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from xgboost import XGBClassifier

# إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Crypto AI Intelligence | منصة توقعات العملات",
    page_icon="🚀",
    layout="wide"
)

# 1. الشريط الجانبي للإعدادات وروابط الإحالة
st.sidebar.title("لوحة التحكم الذكية")
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
st.title("📈 منصة تحليل وتوقع العملات الرقمية بالذكاء الاصطناعي")
st.caption("نظام يعتمد على خوارزميات XGBoost، المؤشرات الفنية، ومؤشر الخوف والجشع لقراءة اتجاه السوق.")
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

# جلب بيانات العملة ومعالجتها
@st.cache_data(ttl=1800)
def load_and_process_data(symbol):
    data = yf.download(symbol, period='3y', progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    data = data.reset_index()
    data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
    
    fng_df = get_fear_and_greed()
    if fng_df is not None:
        data = pd.merge(data, fng_df, on='Date', how='inner')
        
    data.set_index('Date', inplace=True)
    
    # حساب المؤشرات الفنية
    data['Price_Change'] = data['Close'].pct_change()
    data['Volume_Change'] = data['Volume'].pct_change()
    data['SMA_10'] = data['Close'].rolling(10).mean()
    data['SMA_30'] = data['Close'].rolling(30).mean()
    data['SMA_Ratio'] = data['SMA_10'] / data['SMA_30']
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    return data

with st.spinner(f"جاري جلب وتحليل بيانات {crypto_symbol}..."):
    data = load_and_process_data(crypto_symbol)
    features = ['Price_Change', 'Volume_Change', 'SMA_Ratio', 'RSI', 'Fear_Greed_Index']

    today_features = data[features].iloc[-1:]
    data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    clean_data = data.dropna()

    X = clean_data[features]
    y = clean_data['Target']

    model = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42)
    model.fit(X, y)

    prediction = model.predict(today_features)[0]
    probabilities = model.predict_proba(today_features)[0]

# --- عرض النتائج في كروت ---
current_price = float(data['Close'].iloc[-1])
current_fng = int(data['Fear_Greed_Index'].iloc[-1]) if 'Fear_Greed_Index' in data.columns else "N/A"

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="💵 السعر الحالي", value=f"${current_price:,.2f}")

with col2:
    st.metric(label="😨 مؤشر الخوف والجشع", value=f"{current_fng} / 100")

with col3:
    if prediction == 1:
        st.metric(label="🔮 توقع حركة الغد", value="📈 ارتفاع متوقع", delta=f"ثقة النموذج: {probabilities[1]*100:.1f}%")
    else:
        st.metric(label="🔮 توقع حركة الغد", value="📉 انخفاض متوقع", delta=f"ثقة النموذج: {probabilities[0]*100:.1f}%", delta_color="inverse")

st.markdown("---")

# --- الرسوم البيانية ---
st.subheader(f"📊 التحليل الفني لـ {crypto_symbol}")
tab1, tab2 = st.tabs(["📉 حركة السعر التاريخية", "📈 مؤشر القوة النسبية (RSI)"])

with tab1:
    st.line_chart(data['Close'])

with tab2:
    st.line_chart(data['RSI'])
