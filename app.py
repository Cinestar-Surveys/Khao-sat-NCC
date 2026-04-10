import streamlit as st
import pandas as pd
import time
import requests
import os

# =====================================================================
# --- CẤU HÌNH THEME ---
# =====================================================================
os.makedirs('.streamlit', exist_ok=True)
with open('.streamlit/config.toml', 'w') as f:
    f.write("[theme]\nprimaryColor=\"#6f42c1\"\n")

# =====================================================================
# --- CẤU HÌNH BẢO MẬT ---
# =====================================================================
try:
    WEB_APP_URL = st.secrets["WEB_APP_URL"]
    COMPANY_PASSWORD = st.secrets["COMPANY_PASSWORD"]
except KeyError:
    st.error("🚨 Báo động: Chưa cài đặt Mật khẩu trong két sắt Secrets!")
    st.stop()

LOGO_URL = "logo.png"

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Đánh giá NCC Cinestar", layout="wide", page_icon="🍿")

# --- CSS TÙY CHỈNH CHUNG & MẶT NẠ ---
st.markdown("""
    <div class="css-mask-top"></div>
    <div class="css-mask-bottom"></div>
    <style>
    /* ẨN CÁC THÀNH PHẦN MẶC ĐỊNH */
    header, footer, .viewerBadge_container__1QSob {display: none !important; visibility: hidden !important;}
    [data-testid="stHeader"], [data-testid="stFooter"], [data-testid="stToolbar"] {display: none !important;}

    /* MẶT NẠ CHE TÊN GÓC TRÊN VÀ DƯỚI */
    .css-mask-top {
        position: fixed; top: 0; right: 0; width: 300px; height: 60px;
        background-color: var(--background-color); z-index: 9999999;
    }
    .css-mask-bottom {
        position: fixed; bottom: 0; right: 0; width: 100%; height: 50px;
        background-color: var(--background-color); z-index: 9999999;
    }

    /* ĐỊNH DẠNG NÚT BẤM */
    .stButton>button { 
        width: 100%; border-radius: 5px; height: 3em; 
        background-color: #6f42c1 !important; color: white !important; 
        font-weight: bold; border: none; 
    }
    .stButton>button:hover { background-color: #59339d !important; }
    
    .header-container { 
        text-align: center; padding: 20px; border-bottom: 4px solid #6f42c1; 
        margin-bottom: 20px; border-radius: 10px; 
        box-shadow: 0 4px 6px rgba(111, 66, 193, 0.1); 
    }
    
    .welcome-text { 
        font-size: 1.1rem; line-height: 1.6; text-align: center; 
        max-width: 800px; margin: 0 auto; padding: 10px; 
    }

    [data-testid="stForm"] { border: 2px solid #6f42c1 !important; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- QUẢN LÝ ĐIỀU HƯỚNG ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

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
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# =====================================================================
# TRANG 1 & TRANG 2: CĂN GIỮA & KHÔNG CUỘN
# =====================================================================
if st.session_state.current_page in ["login", "welcome"]:
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] { overflow: hidden !important; }
        [data-testid="stMainBlockContainer"] {
            display: flex; flex-direction: column; justify-content: center;
            height: 100vh; padding-top: 0rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

# TRANG 1: LOGIN
if st.session_state.current_page == "login":
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        try: st.image(LOGO_URL, use_container_width=True)
        except: pass
        st.markdown("<h2 style='text-align: center;'>HỆ THỐNG ĐÁNH GIÁ NỘI BỘ</h2>", unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    l, m, r = st.columns([1, 1, 1])
    with m:
        with st.container(border=True):
            pwd = st.text_input("🔑 Mật khẩu truy cập", type="password")
            if st.button("ĐĂNG NHẬP"):
                if pwd == COMPANY_PASSWORD:
                    st.session_state.current_page = "welcome"
                    st.rerun()
                else: st.error("Sai mật khẩu!")

# TRANG 2: WELCOME
elif st.session_state.current_page == "welcome":
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    try: st.image(LOGO_URL, width=200)
    except: pass
    st.markdown("<h1 style='font-size: 2rem;'>Khảo sát đánh giá Nhà cung cấp</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #6f42c1;'>CINESTAR CINEMAS VIETNAM</h3>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="welcome-text">
            Chào mừng bạn đến với hệ thống đánh giá chất lượng nhà cung cấp định kỳ.<br>
            Mọi ý kiến của bạn giúp công ty tối ưu hóa quy trình vận hành.<br><br>
            <i>Hãy dành ít phút để hoàn thành bảng khảo sát này nhé!</i>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("🚀 BẮT ĐẦU ĐÁNH GIÁ", use_container_width=True):
            st.session_state.current_page = "evaluation"
            st.rerun()

# =====================================================================
# TRANG 3: ĐÁNH GIÁ (CUỘN BÌNH THƯỜNG)
# =====================================================================
elif st.session_state.current_page == "evaluation":
    st.sidebar.image(LOGO_URL, use_container_width=True)
    st.sidebar.divider()
    if st.sidebar.button("🚪 Thoát (Đăng xuất)"):
        st.session_state.clear()
        st.rerun()

    st.markdown("<h2>📋 BẢNG ĐÁNH GIÁ CHI TIẾT</h2>", unsafe_allow_html=True)
    df_sites, df_depts, df_questions = load_input_files()
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        evaluator_name = col1.text_input("👤 Họ tên nhân viên")
        selected_site = col2.selectbox("🏢 Chọn Site", ["-- Chọn Site --"] + (df_sites['Site'].dropna().unique().tolist() if not df_sites.empty else []))
        selected_dept = col3.selectbox("📁 Chọn bộ phận", ["-- Chọn Bộ phận --"] + (df_depts[df_depts.columns[0]].dropna().unique().tolist() if not df_depts.empty else []))

    if selected_site != "-- Chọn Site --" and selected_dept != "-- Chọn Bộ phận --" and evaluator_name:
        list_ncc = df_sites[df_sites['Site'] == selected_site]['NCC'].dropna().tolist()
        remaining_nccs = [n for n in list_ncc if n not in st.session_state.evaluated_nccs]
        
        st.divider()
        l_col, r_col = st.columns([1, 2.5])
        with l_col:
            st.write(f"**Tiến độ:** {len(st.session_state.evaluated_nccs)}/{len(list_ncc)} NCC")
            st.progress(len(st.session_state.evaluated_nccs)/len(list_ncc) if list_ncc else 0)
        
        with r_col:
            if remaining_nccs:
                current_ncc = st.selectbox("👉 Đang đánh giá:", remaining_nccs)
                with st.form(key=f"f_{current_ncc}"):
                    df_q_filtered = df_questions[df_questions['Câu hỏi dành cho bộ phận'].astype(str).str.contains(selected_dept, na=False, case=False)]
                    current_answers = []
                    for idx, row in df_q_filtered.groupby(['Nhóm', 'Tiêu chí'], sort=False):
                        st.write(f"**{idx[0]}** - {idx[1]}")
                        opts = df_questions[(df_questions['Tiêu chí'] == idx[1]) & (df_questions['Nhóm'] == idx[0])]
                        choice = st.radio("Chọn:", opts['Lựa chọn'].tolist(), key=f"{current_ncc}_{idx[1]}", horizontal=True)
                        score = opts[opts['Lựa chọn'] == choice]['Điểm'].values[0]
                        current_answers.append({"Thời gian": pd.Timestamp.now(), "NV": evaluator_name, "Bộ phận": selected_dept, "Site": selected_site, "NCC": current_ncc, "Nhóm": idx[0], "Tiêu chí": idx[1], "Lựa chọn": choice, "Điểm": score})
                    
                    if st.form_submit_button("Lưu & Tiếp theo"):
                        st.session_state.all_results_buffer.extend(current_answers)
                        st.session_state.evaluated_nccs.append(current_ncc)
                        st.rerun()
            else:
                st.success("Hoàn thành! Vui lòng bấm gửi.")
                if st.button("🚀 GỬI KẾT QUẢ", type="primary", use_container_width=True):
                    try:
                        res = requests.post(WEB_APP_URL, json=st.session_state.all_results_buffer)
                        if res.status_code == 200:
                            st.session_state.clear()
                            st.balloons()
                            st.success("Gửi thành công!")
                            time.sleep(2)
                            st.rerun()
                    except: st.error("Lỗi gửi dữ liệu.")
