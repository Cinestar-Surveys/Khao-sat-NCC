import streamlit as st
import pandas as pd
import time
import requests

# --- LINK GOOGLE SHEETS WEBHOOK ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzT9_6uEpUe6sFqc-vsM9XmIU4g7gdGEExyi95exYsCB5SrqG8i9B-n6TQ8FrhPCv-2rQ/exec"

st.set_page_config(page_title="Khảo sát NCC", layout="wide")
st.markdown("<style>.header-container { text-align: center; padding-bottom: 20px; margin-bottom: 30px; }</style>", unsafe_allow_html=True)

st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.title("Khảo sát chất lượng nhà cung cấp")
st.info("Lưu ý: Phải đánh giá hết NCC của Site đó mới được chấp thuận câu trả lời.")
st.markdown('</div>', unsafe_allow_html=True)

if 'evaluated_nccs' not in st.session_state: st.session_state.evaluated_nccs = []
if 'all_results_buffer' not in st.session_state: st.session_state.all_results_buffer = []

@st.cache_data
def load_input_files():
    df_sites = pd.read_excel("Danh sách site - NCC.xlsx")
    df_depts = pd.read_excel("Bộ phận đánh giá.xlsx")
    df_qs = pd.read_excel("Câu hỏi khảo sát.xlsx")
    df_qs.columns = df_qs.columns.str.strip().str.replace('\n', '')
    return df_sites, df_depts, df_qs

df_sites, df_depts, df_questions = load_input_files()

col1, col2, col3 = st.columns(3)
evaluator_name = col1.text_input("Nhập họ tên nhân viên đánh giá")
selected_site = col2.selectbox("Chọn Site", ["-- Chọn Site --"] + df_sites['Site'].dropna().unique().tolist())
selected_dept = col3.selectbox("Chọn bộ phận", ["-- Chọn Bộ phận --"] + df_depts[df_depts.columns[0]].dropna().unique().tolist())

if selected_site != "-- Chọn Site --" and selected_dept != "-- Chọn Bộ phận --" and evaluator_name:
    list_ncc = df_sites[df_sites['Site'] == selected_site]['NCC'].dropna().tolist()
    total_ncc = len(list_ncc)
    remaining = [n for n in list_ncc if n not in st.session_state.evaluated_nccs]
    evaluated_count = len(st.session_state.evaluated_nccs)
    
    st.write("---")
    st.markdown(f"### 📊 TIẾN ĐỘ ĐÁNH GIÁ SITE: **{selected_site}**")
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng số NCC", total_ncc)
    m2.metric("Đã đánh giá", evaluated_count)
    m3.metric("Còn lại", len(remaining))
    st.progress(evaluated_count / total_ncc if total_ncc > 0 else 0)

    if len(remaining) > 0:
        current_ncc = remaining[0]
        st.divider()
        st.info(f"👉 **ĐANG ĐÁNH GIÁ: {current_ncc}**")
        
        with st.form(key=f"form_{current_ncc}"):
            df_q_filtered = df_questions[df_questions['Câu hỏi dành cho bộ phận'].astype(str).str.contains(selected_dept, na=False, case=False)]
            current_answers = []
            
            if df_q_filtered.empty:
                st.warning("Bộ phận này chưa có câu hỏi.")
            else:
                for idx, row in df_q_filtered.iterrows():
                    st.write(f"**{row['Nhóm']}** - {row['Tiêu chí']}")
                    options_df = df_questions[(df_questions['Tiêu chí'] == row['Tiêu chí']) & (df_questions['Nhóm'] == row['Nhóm'])]
                    user_choice = st.radio("Chọn mức độ:", options_df['Lựa chọn'].tolist(), key=f"q_{idx}")
                    score = int(options_df[options_df['Lựa chọn'] == user_choice]['Điểm'].values[0])
                    
                    current_answers.append({
                        "Thời gian": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Họ tên NV đánh giá": evaluator_name, "Bộ phận": selected_dept, "Site": selected_site,
                        "Tên NCC": current_ncc, "Nhóm": row['Nhóm'], "Tiêu chí": row['Tiêu chí'],
                        "Lựa chọn": user_choice, "Điểm": score
                    })

            if st.form_submit_button("Lưu & Chuyển NCC tiếp theo"):
                st.session_state.all_results_buffer.extend(current_answers)
                st.session_state.evaluated_nccs.append(current_ncc)
                st.rerun()
    else:
        st.success(f"🎉 Đã hoàn thành toàn bộ {total_ncc} NCC của site {selected_site}!")
        if st.button("XÁC NHẬN VÀ GỬI LÊN HỆ THỐNG", type="primary"):
            with st.spinner("Đang đẩy dữ liệu lên Google Sheet..."):
                try:
                    res = requests.post(WEB_APP_URL, json=st.session_state.all_results_buffer)
                    if res.status_code == 200:
                        st.session_state.evaluated_nccs = []
                        st.session_state.all_results_buffer = []
                        st.balloons()
                        st.success("✅ Đã cập nhật thành công lên Google Sheet!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Lỗi máy chủ Google.")
                except:
                    st.error("Lỗi mạng, không thể gửi dữ liệu.")