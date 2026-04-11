import json
import os
import time

import pandas as pd
import requests
import streamlit as st


# =========================================================
# 1. TẠO FILE THEME CHO STREAMLIT
# Phần này đặt màu chủ đạo cho app.
# =========================================================
# =====================================================================
# --- CẤU HÌNH THEME TỰ ĐỘNG (AUTO DARK/LIGHT MODE)
# =====================================================================
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w", encoding="utf-8") as f:
    f.write(
        """
[theme]
primaryColor="#6f42c1"
"""
    )


def read_config_value(key, default=""):
    # Đọc cấu hình theo thứ tự ưu tiên:
    # 1. Streamlit secrets
    # 2. Biến môi trường
    # 3. Giá trị mặc định
    try:
        value = st.secrets.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass

    env_value = os.getenv(key)
    if env_value is not None and str(env_value).strip():
        return str(env_value).strip()

    return default


# =====================================================================
# --- CẤU HÌNH THÔNG TIN CÔNG TY & BẢO MẬT
# Ưu tiên lấy từ st.secrets, sau đó tới biến môi trường.
# - WEB_APP_URL: URL của Google Apps Script
# - SITE_PASSWORD_SUFFIX: hậu tố mật khẩu theo site, ví dụ "Cinestar"
# - LOGO_URL: file logo dùng để hiển thị
# =====================================================================
WEB_APP_URL = read_config_value("WEB_APP_URL", "")
SITE_PASSWORD_SUFFIX = read_config_value("SITE_PASSWORD_SUFFIX", "Cinestar")
LOGO_URL = read_config_value("LOGO_URL", "logo.png")


# =========================================================
# 2. CẤU HÌNH TRANG CHUNG
# =========================================================
# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Đánh giá NCC Cinestar", layout="wide", page_icon="🍿")


# --- CSS TÙY CHỈNH CHUNG ---
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #6f42c1 !important;
        color: white !important;
        font-weight: bold;
        border: none;
    }

    .stButton>button:hover {
        background-color: #59339d !important;
        color: white !important;
    }

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

    [data-testid="stForm"] {
        border: 2px solid #6f42c1 !important;
        border-radius: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 3. SESSION_STATE
# Dùng để nhớ trạng thái trang và dữ liệu tạm của người dùng.
# =========================================================
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "selected_site" not in st.session_state:
    st.session_state.selected_site = ""
if "evaluated_nccs" not in st.session_state:
    st.session_state.evaluated_nccs = []
if "all_results_buffer" not in st.session_state:
    st.session_state.all_results_buffer = []
if "last_api_status" not in st.session_state:
    st.session_state.last_api_status = None
if "last_api_response" not in st.session_state:
    st.session_state.last_api_response = None


@st.cache_data
def load_input_files():
    # Đọc 3 file Excel đầu vào:
    # - danh sách site và NCC
    # - danh sách bộ phận
    # - bộ câu hỏi khảo sát
    try:
        df_sites = pd.read_excel("Danh sách site - NCC.xlsx")
        df_depts = pd.read_excel("Bộ phận đánh giá.xlsx")
        df_qs = pd.read_excel("Câu hỏi khảo sát.xlsx")
        df_qs.columns = df_qs.columns.str.strip().str.replace("\n", "", regex=False)
        return df_sites, df_depts, df_qs
    except Exception as exc:
        st.error(f"❌ Không tìm thấy hoặc không đọc được file Excel đầu vào: {exc}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def to_json_safe_value(value):
    # Chuẩn hóa dữ liệu trước khi chuyển thành JSON
    # để tránh lỗi kiểu pandas / numpy khi gửi request.
    if pd.isna(value):
        return ""
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def build_payload(rows):
    # Chuyển dữ liệu trong session thành payload chuẩn
    # để gửi lên Google Apps Script.
    payload = []
    for row in rows:
        payload.append(
            {
                "Thời gian": str(to_json_safe_value(row.get("Thời gian", ""))),
                "Họ tên NV đánh giá": str(to_json_safe_value(row.get("Họ tên NV đánh giá", ""))),
                "Bộ phận": str(to_json_safe_value(row.get("Bộ phận", ""))),
                "Site": str(to_json_safe_value(row.get("Site", ""))),
                "Tên NCC": str(to_json_safe_value(row.get("Tên NCC", ""))),
                "Nhóm": str(to_json_safe_value(row.get("Nhóm", ""))),
                "Tiêu chí": str(to_json_safe_value(row.get("Tiêu chí", ""))),
                "Lựa chọn": str(to_json_safe_value(row.get("Lựa chọn", ""))),
                "Điểm": float(to_json_safe_value(row.get("Điểm", 0))),
            }
        )
    return payload


def send_results_to_google_sheet(rows):
    # Hàm này chịu trách nhiệm gửi toàn bộ kết quả
    # sang Google Apps Script bằng POST JSON.
    if not WEB_APP_URL:
        raise ValueError("Chưa cấu hình WEB_APP_URL trong secrets hoặc biến môi trường.")

    payload = build_payload(rows)
    response = requests.post(
        WEB_APP_URL,
        data=json.dumps(payload, ensure_ascii=False),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
    )
    return response, payload


def build_site_password(site_name):
    # Mật khẩu đăng nhập theo quy tắc:
    # Ten Site + "_" + hậu tố cấu hình
    # Ví dụ: "Site A_Cinestar"
    return f"{site_name}_{SITE_PASSWORD_SUFFIX}"


# =====================================================================
# TRANG 1: MÀN HÌNH ĐĂNG NHẬP
# - chọn site và nhập mật khẩu theo site
# - kiểm tra quyền truy cập
# - chuyển sang trang welcome khi đăng nhập đúng
# =====================================================================
if st.session_state.current_page == "login":
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
        }
        [data-testid="stMainBlockContainer"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
            padding-top: 0rem !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    df_sites_login, _, _ = load_input_files()
    site_options = ["-- Chọn Site --"] + (df_sites_login["Site"].dropna().unique().tolist() if not df_sites_login.empty else [])

    col_img1, col_img2, col_img3 = st.columns([1, 1.5, 1])
    with col_img2:
        try:
            st.image(LOGO_URL, use_container_width=True)
        except Exception:
            pass
        st.markdown("<h2 style='text-align: center;'>HỆ THỐNG ĐÁNH GIÁ NỘI BỘ</h2>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 1, 1])
    with col_m:
        with st.container(border=True):
            # Chọn site ngay từ bước đầu để hệ thống biết người dùng thuộc site nào.
            login_site = st.selectbox("🏢 Chọn Site", site_options)
            st.caption('Mật khẩu đăng nhập theo mẫu: "Tên Site_Cinestar"')
            pwd = st.text_input("🔑 Mật khẩu truy cập", type="password")
            if st.button("ĐĂNG NHẬP"):
                if login_site == "-- Chọn Site --":
                    st.error("Vui lòng chọn Site trước khi đăng nhập.")
                elif pwd == build_site_password(login_site):
                    st.session_state.selected_site = login_site
                    st.session_state.current_page = "welcome"
                    st.rerun()
                else:
                    st.error(f'Sai mật khẩu. Mật khẩu đúng phải theo mẫu: "{login_site}_{SITE_PASSWORD_SUFFIX}"')


# =====================================================================
# TRANG 2: LỜI CHÀO MỪNG
# - hiển thị nội dung giới thiệu
# - có nút để chuyển sang trang đánh giá
# =====================================================================
elif st.session_state.current_page == "welcome":
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
        }
        [data-testid="stMainBlockContainer"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        .header-container, .welcome-text {
            text-align: center;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    try:
        st.image(LOGO_URL, width=220)
    except Exception:
        pass

    st.markdown("<h1 style='margin-bottom: 0;'>Khảo sát đánh giá Nhà cung cấp</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0; color: #6f42c1;'>CINESTAR CINEMAS VIETNAM</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="welcome-text">
            <p style="font-size: 1.2rem; margin-bottom: 20px;">
                <b>Hãy để người trải nghiệm trực tiếp lên tiếng!</b>
            </p>
            Chào mừng bạn đến với hệ thống đánh giá chất lượng nhà cung cấp định kỳ.<br>
            Mọi ý kiến của bạn chính là thước đo giúp công ty nhìn nhận đúng năng lực đối tác,<br>
            từ đó nâng cao chất lượng dịch vụ và tối ưu hóa quy trình vận hành.<br><br>
            <i style="color: #666;">Hãy dành ít phút để hoàn thành khảo sát này một cách tâm huyết nhất nhé!</i>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 BẮT ĐẦU ĐÁNH GIÁ NGAY", use_container_width=True):
            st.session_state.current_page = "evaluation"
            st.rerun()


# =====================================================================
# TRANG 3: KHU VỰC THỰC HIỆN ĐÁNH GIÁ
# - chọn thông tin người đánh giá
# - đánh giá lần lượt từng NCC
# - lưu tạm kết quả vào session
# - gửi toàn bộ dữ liệu lên Google Sheet khi hoàn tất
# =====================================================================
elif st.session_state.current_page == "evaluation":
    try:
        st.sidebar.image(LOGO_URL, use_container_width=True)
    except Exception:
        pass

    st.sidebar.divider()
    if st.sidebar.button("🚪 Thoát (Đăng xuất)"):
        st.session_state.clear()
        st.rerun()

    st.markdown("<h2>📋 BẢNG ĐÁNH GIÁ CHI TIẾT</h2>", unsafe_allow_html=True)
    st.caption("Vui lòng điền thông tin và hoàn thành toàn bộ danh sách nhà cung cấp của Site.")

    if not st.session_state.selected_site:
        st.warning("Chưa có Site đăng nhập. Vui lòng quay lại màn hình đăng nhập.")
        st.session_state.current_page = "login"
        st.rerun()

    # Nếu chưa có WEB_APP_URL thì vẫn có thể thao tác,
    # nhưng chưa thể gửi dữ liệu lên Google Sheet.
    if not WEB_APP_URL:
        st.warning("Chưa cấu hình WEB_APP_URL trong Streamlit secrets nên chưa thể gửi dữ liệu lên Google Sheet.")

    df_sites, df_depts, df_questions = load_input_files()

    with st.container(border=True):
        # Khối nhập thông tin chung của người đánh giá
        col1, col2 = st.columns(2)
        evaluator_name = col1.text_input("👤 Họ tên nhân viên đánh giá")
        st.info(f"🏢 Site đăng nhập: {st.session_state.selected_site}")
        selected_dept = col2.selectbox(
            "📁 Chọn bộ phận chuyên môn",
            ["-- Chọn Bộ phận --"] + (df_depts[df_depts.columns[0]].dropna().unique().tolist() if not df_depts.empty else []),
        )

    selected_site = st.session_state.selected_site

    if selected_site and selected_dept != "-- Chọn Bộ phận --" and evaluator_name:
        # Lấy danh sách NCC của site đang chọn
        list_ncc = df_sites[df_sites["Site"] == selected_site]["NCC"].dropna().tolist()
        total_ncc = len(list_ncc)
        # Loại các NCC đã làm xong trong phiên hiện tại
        remaining_nccs = [n for n in list_ncc if n not in st.session_state.evaluated_nccs]
        evaluated_count = len(st.session_state.evaluated_nccs)

        st.divider()
        left_col, right_col = st.columns([1, 2.5])

        with left_col:
            # Cột trái hiển thị tiến độ đánh giá
            st.markdown(f"<h3>🎯 Tiến độ Site: {selected_site}</h3>", unsafe_allow_html=True)
            st.progress(evaluated_count / total_ncc if total_ncc > 0 else 0)
            st.write(f"**Đã hoàn thành:** {evaluated_count} / {total_ncc} NCC")
            st.write("---")
            for ncc in list_ncc:
                if ncc in st.session_state.evaluated_nccs:
                    st.success(f"✅ {ncc}")
                else:
                    st.info(f"⏳ {ncc}")

        with right_col:
            if remaining_nccs:
                # Cột phải là form đánh giá cho NCC hiện tại
                current_ncc = st.selectbox("👉 Chọn NCC cần đánh giá tiếp theo:", remaining_nccs)

                with st.form(key=f"form_{current_ncc}"):
                    # Lọc câu hỏi đúng với bộ phận mà người dùng đã chọn
                    st.markdown(f"<h4 style='color: #6f42c1;'>Đang đánh giá: {current_ncc}</h4>", unsafe_allow_html=True)
                    df_q_filtered = df_questions[
                        df_questions["Câu hỏi dành cho bộ phận"].astype(str).str.contains(selected_dept, na=False, case=False)
                    ]
                    current_answers = []

                    if df_q_filtered.empty:
                        st.warning("Bộ phận của bạn chưa có bộ câu hỏi khảo sát.")
                    else:
                        # Hiển thị từng nhóm/tiêu chí để người dùng chấm điểm
                        for idx, _ in df_q_filtered.groupby(["Nhóm", "Tiêu chí"], sort=False):
                            st.write(f"**{idx[0]}** - {idx[1]}")
                            options_df = df_questions[
                                (df_questions["Tiêu chí"] == idx[1]) & (df_questions["Nhóm"] == idx[0])
                            ]
                            user_choice = st.radio(
                                "Lựa chọn:",
                                options_df["Lựa chọn"].tolist(),
                                key=f"q_{idx[1]}_{current_ncc}",
                            )
                            score_raw = options_df[options_df["Lựa chọn"] == user_choice]["Điểm"].values[0]
                            # Ép về float để tránh lỗi JSON khi gửi dữ liệu
                            score = float(score_raw)

                            # Mỗi câu trả lời tạo thành một dòng dữ liệu sẽ gửi đi sau cùng
                            current_answers.append(
                                {
                                    "Thời gian": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Họ tên NV đánh giá": evaluator_name,
                                    "Bộ phận": selected_dept,
                                    "Site": selected_site,
                                    "Tên NCC": current_ncc,
                                    "Nhóm": idx[0],
                                    "Tiêu chí": idx[1],
                                    "Lựa chọn": user_choice,
                                    "Điểm": score,
                                }
                            )

                    if st.form_submit_button("Lưu & Chuyển sang NCC tiếp theo"):
                        # Chưa gửi lên Google ngay, chỉ lưu tạm vào session
                        st.session_state.all_results_buffer.extend(current_answers)
                        st.session_state.evaluated_nccs.append(current_ncc)
                        st.rerun()
            else:
                # Khi hoàn tất toàn bộ NCC, hiện khu vực gửi dữ liệu
                st.success(f"🎉 Chúc mừng! Bạn đã hoàn thành đánh giá toàn bộ {total_ncc} NCC của {selected_site}.")
                st.info(f"Số dòng chuẩn bị gửi: {len(st.session_state.all_results_buffer)}")

                with st.expander("Xem trước dữ liệu sẽ gửi"):
                    # Cho phép xem lại dữ liệu trước khi bấm gửi
                    st.dataframe(pd.DataFrame(st.session_state.all_results_buffer), use_container_width=True)

                if st.button("🚀 GỬI KẾT QUẢ VÀO HỆ THỐNG", type="primary", use_container_width=True):
                    with st.spinner("Đang truyền dữ liệu bảo mật..."):
                        try:
                            # Gửi dữ liệu sang Google Apps Script
                            response, payload = send_results_to_google_sheet(st.session_state.all_results_buffer)

                            # Ghi lại phản hồi để tiện kiểm tra khi có lỗi
                            st.session_state.last_api_status = response.status_code
                            st.session_state.last_api_response = response.text

                            if response.status_code == 200:
                                st.balloons()
                                st.success("✅ Dữ liệu đã được gửi thành công tới Web App.")
                                st.caption("Nếu Google Sheet vẫn chưa có dữ liệu, hãy kiểm tra mã Google Apps Script ở bước dưới.")
                                st.write("Phản hồi từ máy chủ:", response.text)

                                st.session_state.evaluated_nccs = []
                                st.session_state.all_results_buffer = []
                                time.sleep(2)
                                st.rerun()
                            else:
                                # Google phản hồi lỗi thì hiển thị chi tiết để debug
                                st.error(f"Lỗi máy chủ Google. Status code: {response.status_code}")
                                st.code(response.text or "(response rỗng)")
                                st.caption("Nếu thấy lỗi 302/401/403, thường là Web App chưa deploy public đúng cách.")

                        except requests.exceptions.RequestException as exc:
                            # Lỗi kết nối như timeout, DNS, mạng...
                            st.error(f"Lỗi khi gửi request tới Google Apps Script: {exc}")
                        except Exception as exc:
                            # Lỗi xử lý dữ liệu phía Python trước khi gửi
                            st.error(f"Lỗi xử lý dữ liệu trước khi gửi: {exc}")

                if st.session_state.last_api_status is not None:
                    # Khu debug phản hồi lần gửi gần nhất
                    st.write(f"Status code lần gửi gần nhất: {st.session_state.last_api_status}")
                    st.code(st.session_state.last_api_response or "(response rỗng)")
