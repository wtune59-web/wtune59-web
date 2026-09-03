# --- تحديث قائمة أصول الذكاء الاصطناعي والماسح الشامل ---

# القائمة الافتراضية المحدثة لتشمل عملاقة الذكاء الاصطناعي والسيولة
default_ai_crypto_list = ["TAO-USD", "RENDER-USD", "FET-USD", "NEAR-USD", "BTC-USD", "ETH-USD", "SOL-USD"]

if app_mode == "ماسح السوق الشامل (Market Screener)":
    st.title("🗺️ ماسح السوق الشامل لعملات الذكاء الاصطناعي والفرص الرقمية")
    st.caption("فحص ذكي لأقوى مشاريع البلوكشين والذكاء الاصطناعي عبر خوارزميات التنبؤ اللحظي.")
    
    s_input = st.text_input("الأصول المراد فحصها (رمز Yahoo Finance):", value=", ".join(default_ai_crypto_list))
    assets_l = [x.strip().upper() for x in s_input.split(',')]
    
    if st.button("🚀 تشغيل ماسح قطاع الذكاء الاصطناعي"):
        res = []
        with st.spinner("جاري تحليل أسواق الذكاء الاصطناعي والسيولة اللحظية..."):
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
                        fng_v = float(df_temp['Fear_Greed_Index'].iloc[-1])
                        
                        dec = "📈 شراء" if pred_val == 1 and max_conf >= conf_threshold_input else ("📉 بيع" if pred_val == 0 and max_conf >= conf_threshold_input else "⚠️ ترقب")
                        res.append({
                            "الأصل": ast, 
                            "السعر الحالي": f"${px_v:,.2f}", 
                            "قوة الاتجاه ADX": f"{adx_v:.1f}", 
                            "مؤشر الخوف/الطمع": f"{fng_v:.0f}",
                            "قرار النظام الذكي": dec, 
                            "نسبة الثقة": f"{max_conf*100:.1f}%"
                        })
        if res:
            st.table(pd.DataFrame(res))
        else:
            st.warning("لم يتم العثور على بيانات كافية للأصول المدخلة. تأكد من صحة الرموز (مثل TAO-USD).")

# إضافة فئة عملات الذكاء الاصطناعي للقائمة الجانبية التحليلية الفردية
elif app_mode == "تحليل فردي معمق وإدارة الأصول":
    market_category = st.sidebar.selectbox("اختر فئة السوق:", ["عملات الذكاء الاصطناعي (AI Crypto)", "عملات رقمية عامة (Crypto)", "أسهم عالمية (Stocks)"])
    
    if market_category == "عملات الذكاء الاصطناعي (AI Crypto)":
        default_sym = "TAO-USD"
    elif market_category == "عملات رقمية عامة (Crypto)":
        default_sym = "BTC-USD"
    else:
        default_sym = "AAPL"
        
    user_symbol_input = st.sidebar.text_input("أو أدخل الرمز المباشر:", value=default_sym)
    crypto_symbol = user_symbol_input.strip().upper()
