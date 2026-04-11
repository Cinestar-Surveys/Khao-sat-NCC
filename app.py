import streamlit as st
import pandas as pd
import time
import requests
import os

# =====================================================================
# --- CẤU HÌNH THEME TỰ ĐỘNG (AUTO DARK/LIGHT MODE) ---
# Chỉ giữ lại màu Tím làm màu chủ đạo (Primary Color) cho thanh tiến độ, checkbox...
# Còn lại Nền và Chữ sẽ tự động đổi Trắng/Đen theo máy tính của người dùng.
# =====================================================================
os.makedirs('.streamlit', exist_ok=True)
with open('.streamlit/config.toml', 'w') as f:
    f.write("""
[theme]
primaryColor="#6f42c1"
    """)

# =====================================================================
# --- CẤU HÌNH THÔNG TIN CÔNG TY & BẢO MẬT ---
# =====================================================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzT9_6uEpUe6sFqc-vsM9XmIU4g7gdGEExyi95exYsCB5SrqG8i9B-n6TQ8FrhPCv-2rQ/exec"
COMPANY_PASSWORD = "Cinestar" 
LOGO_URL = "logo.png" 

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Đánh giá NCC Cinestar", layout="wide", page_icon="🍿")

# --- CSS TÙY CHỈNH CHUNG ---
st.markdown("""
    <style>
    /* =========================================
       ẨN CÁC THÀNH PHẦN MẶC ĐỊNH CỦA STREAMLIT
       ========================================= */
    #MainMenu {visibility: hidden;} /* Ẩn Menu Hamburger & Deploy góc trên phải */
    footer {visibility: hidden;}    /* Ẩn chữ Made with Streamlit dưới cùng */
    header {visibility: hidden;}    /* Ẩn khoảng trắng trên cùng */

    /* Nút bấm mặc định: Tím (#6f42c1) */
    .stButton>button { 
        width: 100%; 
        border-radius: 5px; 
        height: 3em; 
        background-color: #6f42c1 !important; 
        color: white !important; 
        font-weight: bold; 
        border: none; 
    }
    
    /* Màu nút bấm khi rê chuột vào */
    .stButton>button:hover { 
        background-color: #59339d !important; 
        color: white !important; 
    }
    
    /* Đường viền dưới của Header (Không set màu nền để tự thích ứng Dark/Light) */
    .header-container { 
        text-align: center; 
        padding: 20px; 
        border-bottom: 4px solid #6f42c1; 
        margin-bottom: 20px; 
        border-radius: 10px; 
        box-shadow: 0 4px 6px rgba(111, 66, 193, 0.2); 
    }
    
    .welcome-text { 
        font-size: 1.2rem; 
        line-height: 1.6; 
        text-align: center; 
        max-width: 800px; 
        margin: 0 auto; 
        padding: 20px; 
    }
    
    /* Đảm bảo Form luôn có viền Tím nổi bật */
    [data-testid="stForm"] {
        border: 2px solid #6f42c1 !important;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- QUẢN LÝ ĐIỀU HƯỚNG TRANG (ROUTER) ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

# Quản lý bộ nhớ dữ liệu đánh giá
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
        st.error("❌ Lỗi: Không tìm thấy các file Excel đầu vào trong thư mục.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# =====================================================================
# TRANG 1: MÀN HÌNH ĐĂNG NHẬP
# =====================================================================
if st.session_state.current_page == "login":
    # --- THÊM CSS KHÓA CUỘN & CĂN GIỮA DỌC DÀNH RIÊNG CHO TRANG LOGIN ---
    st.markdown("""
        <style>
        /* Khóa thanh cuộn toàn bộ trang */
        [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
        }
        /* Ép nội dung nằm ngay giữa chiều cao màn hình (100vh) */
        [data-testid="stMainBlockContainer"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
            padding-top: 0rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col_img1, col_img2, col_img3 = st.columns([1, 1.5, 1])
    with col_img2:
        try:
            st.image(LOGO_URL, use_container_width=True)
        except:
            pass 
        st.markdown("<h2 style='text-align: center;'>HỆ THỐNG ĐÁNH GIÁ NỘI BỘ</h2>", unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 1, 1])
    with col_m:
        with st.container(border=True):
            pwd = st.text_input("🔑 Mật khẩu truy cập", type="password")
            if st.button("ĐĂNG NHẬP"):
                if pwd == COMPANY_PASSWORD:
                    st.session_state.current_page = "welcome"
                    st.rerun()
                else:
                    st.error("Sai mật khẩu! Vui lòng thử lại.")

# =====================================================================
# TRANG 2: LỜI CHÀO MỪNG & GIỚI THIỆU
# =====================================================================
# =====================================================================
# TRANG 2: LỜI CHÀO MỪNG (ĐỊNH DẠNG GIỮA, KHÔNG CUỘN)
# =====================================================================
elif st.session_state.current_page == "welcome":
    # 1. CSS DÀNH RIÊNG CHO TRANG WELCOME ĐỂ CĂN GIỮA & KHÓA CUỘN
    st.markdown("""
        <style>
        /* Khóa thanh cuộn */
        [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
        }
        /* Căn giữa tuyệt đối nội dung */
        [data-testid="stMainBlockContainer"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        /* Căn giữa text bên trong container */
        .header-container, .welcome-text {
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. NỘI DUNG HIỂN THỊ
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    try:
        # Giảm size logo một chút để đảm bảo vừa khít màn hình không bị kích hoạt cuộn
        st.image(LOGO_URL, width=220)
    except:
        pass
    
    st.markdown("<h1 style='margin-bottom: 0;'>Khảo sát đánh giá Nhà cung cấp</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0; color: #6f42c1;'>CINESTAR CINEMAS VIETNAM</h2>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="welcome-text">
            <p style="font-size: 1.2rem; margin-bottom: 20px;">
                <b>Hãy để người trải nghiệm trực tiếp lên tiếng!</b>
            </p>
            Chào mừng bạn đến với hệ thống đánh giá chất lượng nhà cung cấp định kỳ.<br>
            Mọi ý kiến của bạn chính là thước đo giúp công ty nhìn nhận đúng năng lực đối tác,<br>
            từ đó nâng cao chất lượng dịch vụ và tối ưu hóa quy trình vận hành.<br><br>
            <i style="color: #666;">Hãy dành ít phút để hoàn thành khảo sát này một cách tâm huyết nhất nhé!</i>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    
    # 3. NÚT BẤM CĂN GIỮA
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 BẮT ĐẦU ĐÁNH GIÁ NGAY", use_container_width=True):
            st.session_state.current_page = "evaluation"
            st.rerun()

# =====================================================================
# TRANG 3: KHU VỰC THỰC HIỆN ĐÁNH GIÁ (MAIN APP)
# =====================================================================
elif st.session_state.current_page == "evaluation":
    try:
        st.sidebar.image(LOGO_URL, use_container_width=True)
    except:
        pass
        
    st.sidebar.divider()
    # Nút thoát nằm ngay dưới đường kẻ ở sidebar
    if st.sidebar.button("🚪 Thoát (Đăng xuất)"):
        st.session_state.clear()
        st.rerun()

    st.markdown("<h2>📋 BẢNG ĐÁNH GIÁ CHI TIẾT</h2>", unsafe_allow_html=True)
    st.caption("Vui lòng điền thông tin và hoàn thành toàn bộ danh sách nhà cung cấp của Site.")
    
    df_sites, df_depts, df_questions = load_input_files()
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        evaluator_name = col1.text_input("👤 Họ tên nhân viên đánh giá")
        selected_site = col2.selectbox("🏢 Chọn Site công tác", ["-- Chọn Site --"] + (df_sites['Site'].dropna().unique().tolist() if not df_sites.empty else []))
        selected_dept = col3.selectbox("📁 Chọn bộ phận chuyên môn", ["-- Chọn Bộ phận --"] + (df_depts[df_depts.columns[0]].dropna().unique().tolist() if not df_depts.empty else []))

    if selected_site != "-- Chọn Site --" and selected_dept != "-- Chọn Bộ phận --" and evaluator_name:
        list_ncc = df_sites[df_sites['Site'] == selected_site]['NCC'].dropna().tolist()
        total_ncc = len(list_ncc)
        remaining_nccs = [n for n in list_ncc if n not in st.session_state.evaluated_nccs]
        evaluated_count = len(st.session_state.evaluated_nccs)
        
        st.divider()
        left_col, right_col = st.columns([1, 2.5])
        
        # CỘT TRÁI: CHECKLIST NCC
        with left_col:
            st.markdown(f"<h3>🎯 Tiến độ Site: {selected_site}</h3>", unsafe_allow_html=True)
            st.progress(evaluated_count / total_ncc if total_ncc > 0 else 0)
            st.write(f"**Đã hoàn thành:** {evaluated_count} / {total_ncc} NCC")
            st.write("---")
            for ncc in list_ncc:
                if ncc in st.session_state.evaluated_nccs:
                    st.success(f"✅ {ncc}")
                else:
                    st.info(f"⏳ {ncc}")

        # CỘT PHẢI: FORM CÂU HỎI
        with right_col:
            if len(remaining_nccs) > 0:
                current_ncc = st.selectbox("👉 Chọn NCC cần đánh giá tiếp theo:", remaining_nccs)
                
                with st.form(key=f"form_{current_ncc}"):
                    # Chỗ này giữ lại màu Tím để làm nổi bật tên NCC đang đánh giá
                    st.markdown(f"<h4 style='color: #6f42c1;'>Đang đánh giá: {current_ncc}</h4>", unsafe_allow_html=True)
                    df_q_filtered = df_questions[df_questions['Câu hỏi dành cho bộ phận'].astype(str).str.contains(selected_dept, na=False, case=False)]
                    current_answers = []
                    
                    if df_q_filtered.empty:
                        st.warning("Bộ phận của bạn chưa có bộ câu hỏi khảo sát.")
                    else:
                        for idx, row in df_q_filtered.groupby(['Nhóm', 'Tiêu chí'], sort=False):
                            st.write(f"**{idx[0]}** - {idx[1]}")
                            options_df = df_questions[(df_questions['Tiêu chí'] == idx[1]) & (df_questions['Nhóm'] == idx[0])]
                            user_choice = st.radio("Lựa chọn:", options_df['Lựa chọn'].tolist(), key=f"q_{idx[1]}_{current_ncc}")
                            score = options_df[options_df['Lựa chọn'] == user_choice]['Điểm'].values[0]
                            
                            current_answers.append({
                                "Thời gian": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Họ tên NV đánh giá": evaluator_name, "Bộ phận": selected_dept, "Site": selected_site,
                                "Tên NCC": current_ncc, "Nhóm": idx[0], "Tiêu chí": idx[1], "Lựa chọn": user_choice, "Điểm": score
                            })

                    if st.form_submit_button("Lưu & Chuyển sang NCC tiếp theo"):
                        st.session_state.all_results_buffer.extend(current_answers)
                        st.session_state.evaluated_nccs.append(current_ncc)
                        st.rerun()
            else:
                st.success(f"🎉 Chúc mừng! Bạn đã hoàn thành đánh giá toàn bộ {total_ncc} NCC của {selected_site}.")
                if st.button("🚀 GỬI KẾT QUẢ VÀO HỆ THỐNG", type="primary", use_container_width=True):
                    with st.spinner('Đang truyền dữ liệu bảo mật...'):
                        try:
                            res = requests.post(WEB_APP_URL, json=st.session_state.all_results_buffer)
                            if res.status_code == 200:
                                st.session_state.evaluated_nccs = []
                                st.session_state.all_results_buffer = []
                                st.balloons()
                                st.success("✅ Dữ liệu đã được lưu trữ thành công!")
                                time.sleep(2)
                                st.rerun()
                            else: st.error("Lỗi kết nối máy chủ Google.")
                        except: st.error("Lỗi mạng, vui lòng kiểm tra kết nối.")
