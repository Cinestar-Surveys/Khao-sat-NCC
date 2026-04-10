import streamlit as st
import pandas as pd
import time
import requests

# --- CẤU HÌNH BẢO MẬT & KẾT NỐI ---
# 1. Điền link Google Sheet của bạn vào đây
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzT9_6uEpUe6sFqc-vsM9XmIU4g7gdGEExyi95exYsCB5SrqG8i9B-n6TQ8FrhPCv-2rQ/exec"
# 2. Đặt mật khẩu nội bộ cho công ty bạn ở đây
COMPANY_PASSWORD = "Cinestar" 

st.set_page_config(page_title="Khảo sát NCC", layout="wide")

# --- MÀN HÌNH ĐĂNG NHẬP ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; margin-top: 50px;'>🔒 HỆ THỐNG ĐÁNH GIÁ NỘI BỘ</h2>", unsafe_allow_html=True)
    st.info("Vui lòng nhập mật khẩu để truy cập hệ thống.")
    
    col_l, col_m, col_r = st.columns([1, 1, 1])
    with col_m:
        pwd = st.text_input("Mật khẩu truy cập", type="password")
        if st.button("Đăng nhập", use_container_width=True):
            if pwd == COMPANY_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Sai mật khẩu! Vui lòng thử lại.")
    st.stop() # Dừng toàn bộ code bên dưới nếu chưa đăng nhập thành công

# =====================================================================
# --- TỪ ĐÂY TRỞ XUỐNG CHỈ HIỂN THỊ KHI ĐÃ NHẬP ĐÚNG MẬT KHẨU ---
# =====================================================================

st.markdown("<style>.header-container { text-align: center; padding-bottom: 20px; margin-bottom: 30px; }</style>", unsafe_allow_html=True)

st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.title("Khảo sát chất lượng nhà cung cấp")
st.info("Lưu ý: Bạn có thể chọn bất kỳ NCC nào để đánh giá trước, nhưng PHẢI hoàn thành toàn bộ danh sách mới được phép gửi kết quả.")
st.markdown('</div>', unsafe_allow_html=True)

# Quản lý bộ nhớ
if 'evaluated_nccs' not in st.session_state: st.session_state.evaluated_nccs = []
if 'all_results_buffer' not in st.session_state: st.session_state.all_results_buffer = []

@st.cache_data
def load_input_files():
    try:
        df_sites = pd.read_excel("Danh sách site - NCC.xlsx")
        df_depts = pd.read_excel("Bộ phận đánh giá.xlsx")
        df_qs = pd.read_excel("Câu hỏi khảo sát.xlsx")
        df_qs.columns = df_qs.columns.str.strip().str.replace('\n', '')
        return df_sites, df_depts, df_qs
    except Exception:
        st.error("Lỗi đọc file Excel. Vui lòng kiểm tra lại 3 file đầu vào.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_sites, df_depts, df_questions = load_input_files()

col1, col2, col3 = st.columns(3)
evaluator_name = col1.text_input("Nhập họ tên NV đánh giá")
selected_site = col2.selectbox("Chọn Site", ["-- Chọn Site --"] + df_sites['Site'].dropna().unique().tolist() if not df_sites.empty else [])
selected_dept = col3.selectbox("Chọn bộ phận", ["-- Chọn Bộ phận --"] + df_depts[df_depts.columns[0]].dropna().unique().tolist() if not df_depts.empty else [])

if selected_site != "-- Chọn Site --" and selected_dept != "-- Chọn Bộ phận --" and evaluator_name:
    # Lấy danh sách NCC
    list_ncc = df_sites[df_sites['Site'] == selected_site]['NCC'].dropna().tolist()
    total_ncc = len(list_ncc)
    remaining_nccs = [n for n in list_ncc if n not in st.session_state.evaluated_nccs]
    evaluated_count = len(st.session_state.evaluated_nccs)
    
    st.write("---")
    
    # --- GIAO DIỆN CHIA 2 CỘT: DANH SÁCH BÊN TRÁI, FORM BÊN PHẢI ---
    left_col, right_col = st.columns([1, 2.5])
    
    with left_col:
        st.markdown(f"### 📋 Trạng thái Site: **{selected_site}**")
        st.progress(evaluated_count / total_ncc if total_ncc > 0 else 0)
        st.caption(f"Đã đánh giá: {evaluated_count} / {total_ncc}")
        
        # Tạo Checklist trực quan
        st.write("**Danh sách NCC:**")
        for ncc in list_ncc:
            if ncc in st.session_state.evaluated_nccs:
                st.success(f"✅ {ncc}") # Đã làm
            else:
                st.warning(f"⏳ {ncc}") # Chưa làm

    with right_col:
        if len(remaining_nccs) > 0:
            st.markdown("### ✍️ Thực hiện đánh giá")
            # --- QUYỀN LỰA CHỌN NCC Ở ĐÂY ---
            current_ncc = st.selectbox("Chọn nhà cung cấp muốn đánh giá bây giờ:", remaining_nccs)
            st.divider()
            
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

                if st.form_submit_button("Lưu & Chuyển NCC khác"):
                    st.session_state.all_results_buffer.extend(current_answers)
                    st.session_state.evaluated_nccs.append(current_ncc)
                    st.rerun()
        else:
            st.success(f"🎉 Xuất sắc! Bạn đã đánh giá xong toàn bộ {total_ncc} NCC.")
            st.info("Vui lòng bấm nút bên dưới để hệ thống ghi nhận kết quả cuối cùng.")
            if st.button("🚀 XÁC NHẬN VÀ GỬI LÊN HỆ THỐNG", type="primary", use_container_width=True):
                with st.spinner("Đang đẩy dữ liệu lên Google Sheet..."):
                    try:
                        res = requests.post(WEB_APP_URL, json=st.session_state.all_results_buffer)
                        if res.status_code == 200:
                            st.session_state.evaluated_nccs = []
                            st.session_state.all_results_buffer = []
                            st.balloons()
                            st.success("✅ Đã ghi nhận thành công! Bạn có thể chuyển sang Site khác.")
                            time.sleep(2.5)
                            st.rerun()
                        else:
                            st.error(f"Lỗi máy chủ Google ({res.status_code}).")
                    except Exception as e:
                        st.error(f"Lỗi kết nối mạng: {e}")
