import base64
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


def get_logo_data_uri(image_path):
    # Chuyển file logo thành data URI để có thể nhúng trực tiếp vào HTML/CSS.
    if not image_path or not os.path.exists(image_path):
        return ""

    extension = os.path.splitext(image_path)[1].lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(extension, "application/octet-stream")

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


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
if "current_ncc_selector" not in st.session_state:
    st.session_state.current_ncc_selector = ""
if "current_ncc_widget" not in st.session_state:
    st.session_state.current_ncc_widget = ""
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

        # Nếu file Excel có merge cell hoặc để trống lặp lại ở các dòng lựa chọn,
        # cần fill xuống để mỗi dòng lựa chọn vẫn mang đủ thông tin Nhóm/Tiêu chí/Bộ phận.
        for column in ["Nhóm", "Tiêu chí", "Câu hỏi dành cho bộ phận"]:
            if column in df_qs.columns:
                df_qs[column] = df_qs[column].ffill()

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


def replace_ncc_results(ncc_name, new_answers):
    # Xóa dữ liệu cũ của NCC này nếu đã từng lưu,
    # rồi thay bằng dữ liệu mới để tránh trùng lặp.
    st.session_state.all_results_buffer = [
        row for row in st.session_state.all_results_buffer if row.get("Tên NCC") != ncc_name
    ]
    st.session_state.all_results_buffer.extend(new_answers)

    if ncc_name not in st.session_state.evaluated_nccs:
        st.session_state.evaluated_nccs.append(ncc_name)


def clear_question_widget_states():
    # Xóa các widget câu hỏi sau khi gửi thành công
    # để phiên đánh giá mới không bị giữ lại đáp án cũ.
    for key in list(st.session_state.keys()):
        if str(key).startswith("q_"):
            del st.session_state[key]


def get_next_pending_ncc(list_ncc):
    # Trả về NCC chưa hoàn thành tiếp theo.
    # Nếu tất cả đã hoàn thành thì giữ nguyên NCC đang chọn hoặc lấy NCC đầu tiên.
    evaluated_set = set(st.session_state.evaluated_nccs)
    for ncc in list_ncc:
        if ncc not in evaluated_set:
            return ncc

    if st.session_state.current_ncc_selector in list_ncc:
        return st.session_state.current_ncc_selector

    return list_ncc[0] if list_ncc else ""


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
            pwd = st.text_input("🔑 Mật khẩu truy cập", type="password")
            if st.button("ĐĂNG NHẬP"):
                if login_site == "-- Chọn Site --":
                    st.error("Vui lòng chọn Site trước khi đăng nhập.")
                elif pwd == build_site_password(login_site):
                    st.session_state.selected_site = login_site
                    st.session_state.current_page = "welcome"
                    st.rerun()
                else:
                    st.error("Sai mật khẩu. Vui lòng kiểm tra lại thông tin đăng nhập.")


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
            min-height: 100vh;
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            display: flex;
            align-items: center;
        }
        .welcome-stage {
            max-width: 1120px;
            margin: 0 auto;
            width: 100%;
        }
        .welcome-card {
            position: relative;
            overflow: hidden;
            padding: 2.15rem 2.45rem;
            border-radius: 28px;
            border: 1px solid rgba(111, 66, 193, 0.16);
            background:
                radial-gradient(circle at top right, rgba(111, 66, 193, 0.10), transparent 32%),
                linear-gradient(135deg, rgba(255,255,255,0.98), rgba(248,244,255,0.96));
            box-shadow: 0 24px 60px rgba(54, 44, 92, 0.10);
        }
        .welcome-card::after {
            content: "";
            position: absolute;
            inset: auto 0 0 0;
            height: 6px;
            background: linear-gradient(90deg, #6f42c1, #8f63dd, #6f42c1);
        }
        .welcome-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.9rem;
            border-radius: 999px;
            background: rgba(111, 66, 193, 0.10);
            color: #6f42c1;
            font-weight: 700;
            font-size: 0.92rem;
            letter-spacing: 0.02em;
            width: fit-content;
            margin-bottom: 1.1rem;
        }
        .welcome-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.9fr);
            gap: 1.5rem;
            align-items: center;
        }
        .welcome-brand img {
            max-width: 220px;
        }
        .welcome-title {
            margin: 1rem 0 0.55rem 0;
            font-size: clamp(2.35rem, 4vw, 4rem);
            line-height: 1.06;
            font-weight: 800;
            color: #23283b;
            letter-spacing: -0.03em;
        }
        .welcome-subtitle {
            margin: 0 0 1.25rem 0;
            color: #6f42c1;
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .welcome-lead {
            margin: 0 0 0.9rem 0;
            font-size: 1.18rem;
            font-weight: 700;
            color: #2e3347;
        }
        .welcome-copy {
            margin: 0;
            font-size: 1.06rem;
            line-height: 1.8;
            color: #50556b;
            max-width: 680px;
        }
        .welcome-note {
            margin-top: 1.1rem;
            font-size: 1.04rem;
            font-style: italic;
            color: #6c7286;
        }
        .welcome-side {
            padding: 1.5rem;
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(111, 66, 193, 0.11), rgba(111, 66, 193, 0.05));
            border: 1px solid rgba(111, 66, 193, 0.14);
        }
        .welcome-side-title {
            margin: 0 0 1rem 0;
            font-size: 1rem;
            font-weight: 800;
            color: #2d3042;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .welcome-chip {
            display: block;
            width: 100%;
            margin-bottom: 0.75rem;
            padding: 0.9rem 1rem;
            border-radius: 16px;
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(111, 66, 193, 0.08);
            color: #31364a;
            font-size: 0.98rem;
            line-height: 1.45;
        }
        .welcome-chip strong {
            display: block;
            margin-bottom: 0.16rem;
            color: #6f42c1;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .welcome-actions {
            max-width: 520px;
            margin: 0.85rem auto 0 auto;
            text-align: center;
        }
        .welcome-actions p {
            margin: 0 0 0.55rem 0;
            color: #646b80;
            font-size: 0.92rem;
        }
        .welcome-cta-slot {
            max-width: 520px;
            margin: 0 auto;
        }
        @media (max-width: 900px) {
            [data-testid="stAppViewContainer"] {
                overflow: auto !important;
            }
            [data-testid="stMainBlockContainer"] {
                display: block;
                min-height: auto;
                padding-top: 1.25rem !important;
                padding-bottom: 1.25rem !important;
            }
            .welcome-card {
                min-height: auto;
                padding: 1.5rem 1.15rem;
                border-radius: 22px;
            }
            .welcome-grid {
                grid-template-columns: 1fr;
            }
            .welcome-brand img {
                max-width: 180px;
            }
            .welcome-actions {
                margin-top: 1.35rem;
            }
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    current_site = st.session_state.selected_site or "Site đã chọn"
    logo_data_uri = get_logo_data_uri(LOGO_URL)
    logo_markup = f'<div class="welcome-brand"><img src="{logo_data_uri}" alt="Cinestar logo"></div>' if logo_data_uri else ""

    st.markdown('<div class="welcome-stage">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="welcome-card">
            <div class="welcome-badge">KHỞI ĐỘNG KHẢO SÁT NỘI BỘ</div>
            <div class="welcome-grid">
                <div>
                    {logo_markup}
                    <h1 class="welcome-title">Khảo sát đánh giá Nhà cung cấp</h1>
                    <p class="welcome-subtitle">Cinestar Cinemas Vietnam</p>
                    <p class="welcome-lead">Hãy để người trải nghiệm trực tiếp lên tiếng!</p>
                    <p class="welcome-copy">
                        Chào mừng bạn đến với hệ thống đánh giá chất lượng nhà cung cấp định kỳ.
                        Mọi ý kiến của bạn là cơ sở để công ty nhìn nhận đúng năng lực đối tác,
                        từ đó nâng cao chất lượng dịch vụ và tối ưu hóa vận hành tại từng site.
                    </p>
                    <p class="welcome-note">
                        Hoàn thành khảo sát với góc nhìn thực tế, khách quan và đầy đủ nhất để kết quả phản ánh đúng chất lượng hợp tác.
                    </p>
                </div>
                <div class="welcome-side">
                    <p class="welcome-side-title">Thông Tin Phiên Đánh Giá</p>
                    <div class="welcome-chip">
                        <strong>Site đăng nhập</strong>
                        {current_site}
                    </div>
                    <div class="welcome-chip">
                        <strong>Phạm vi khảo sát</strong>
                        Chỉ hiển thị đúng danh sách nhà cung cấp thuộc site đang đăng nhập.
                    </div>
                    <div class="welcome-chip" style="margin-bottom: 0;">
                        <strong>Mục tiêu</strong>
                        Đánh giá định kỳ để cải thiện chất lượng dịch vụ, tiến độ và mức độ phối hợp.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="welcome-actions"><p>Sẵn sàng bắt đầu? Nhấn nút bên dưới để chuyển sang danh sách đánh giá của site.</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.35, 1, 1.35])
    with col2:
        if st.button("🚀 BẮT ĐẦU ĐÁNH GIÁ NGAY", use_container_width=True):
            st.session_state.current_page = "evaluation"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


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
        evaluated_nccs_for_site = [ncc for ncc in list_ncc if ncc in set(st.session_state.evaluated_nccs)]
        evaluated_count = len(evaluated_nccs_for_site)

        st.divider()
        left_col, right_col = st.columns([1, 2.5])

        with left_col:
            # Cột trái hiển thị tiến độ đánh giá
            st.markdown(f"<h3>🎯 Tiến độ Site: {selected_site}</h3>", unsafe_allow_html=True)
            st.progress(evaluated_count / total_ncc if total_ncc > 0 else 0)
            st.write(f"**Đã hoàn thành:** {evaluated_count} / {total_ncc} NCC")
            st.write("---")
            for ncc in list_ncc:
                if ncc in evaluated_nccs_for_site:
                    st.success(f"✅ {ncc}")
                else:
                    st.info(f"⏳ {ncc}")

        with right_col:
            if list_ncc:
                # Tự động trỏ tới NCC chưa hoàn thành tiếp theo để thao tác nhanh hơn.
                if st.session_state.current_ncc_selector not in list_ncc:
                    st.session_state.current_ncc_selector = get_next_pending_ncc(list_ncc)
                if st.session_state.current_ncc_widget not in list_ncc:
                    st.session_state.current_ncc_widget = st.session_state.current_ncc_selector
                elif st.session_state.current_ncc_widget != st.session_state.current_ncc_selector:
                    st.session_state.current_ncc_widget = st.session_state.current_ncc_selector

                # Cột phải là form đánh giá cho NCC hiện tại.
                # Người dùng có thể chọn lại cả NCC đã hoàn thành để sửa kết quả.
                current_ncc = st.selectbox(
                    "👉 Chọn NCC để đánh giá hoặc đánh giá lại:",
                    list_ncc,
                    key="current_ncc_widget",
                    format_func=lambda ncc: f"✅ {ncc}" if ncc in evaluated_nccs_for_site else f"⏳ {ncc}",
                )
                st.session_state.current_ncc_selector = current_ncc

                if current_ncc in evaluated_nccs_for_site:
                    st.info("NCC này đã được lưu trước đó. Nếu bạn chỉnh lại và bấm lưu, hệ thống sẽ thay kết quả cũ bằng kết quả mới.")

                with st.form(key=f"form_{current_ncc}"):
                    # Lọc câu hỏi đúng với bộ phận mà người dùng đã chọn
                    st.markdown(f"<h4 style='color: #6f42c1;'>Đang đánh giá: {current_ncc}</h4>", unsafe_allow_html=True)
                    df_q_filtered = df_questions[
                        df_questions["Câu hỏi dành cho bộ phận"].astype(str).str.contains(selected_dept, na=False, case=False)
                    ]
                    current_answers = []
                    unanswered_questions = []

                    if df_q_filtered.empty:
                        st.warning("Bộ phận của bạn chưa có bộ câu hỏi khảo sát.")
                    else:
                        # Hiển thị theo từng Nhóm.
                        # Trong mỗi Nhóm sẽ liệt kê toàn bộ câu hỏi/tiêu chí của nhóm đó.
                        for group_name, group_df in df_q_filtered.groupby("Nhóm", sort=False):
                            st.markdown(f"### {group_name}")

                            criteria_in_group = list(dict.fromkeys(group_df["Tiêu chí"].dropna().astype(str).tolist()))

                            for criterion in criteria_in_group:
                                st.markdown(f"**{criterion}**")
                                options_df = group_df[group_df["Tiêu chí"].astype(str) == criterion].copy()
                                choice_options = list(
                                    dict.fromkeys(options_df["Lựa chọn"].dropna().astype(str).tolist())
                                )

                                if not choice_options:
                                    st.warning(f"Tiêu chí '{criterion}' hiện chưa có lựa chọn đánh giá trong file Excel.")
                                    unanswered_questions.append(f"{group_name} - {criterion}")
                                    continue

                                user_choice = st.radio(
                                    "Chọn mức đánh giá",
                                    choice_options,
                                    key=f"q_{selected_dept}_{group_name}_{criterion}_{current_ncc}",
                                    index=None,
                                    label_visibility="collapsed",
                                )

                                if user_choice is None:
                                    unanswered_questions.append(f"{group_name} - {criterion}")
                                else:
                                    score_series = options_df.loc[
                                        options_df["Lựa chọn"].astype(str) == str(user_choice), "Điểm"
                                    ]
                                    score_raw = score_series.iloc[0]
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
                                            "Nhóm": group_name,
                                            "Tiêu chí": criterion,
                                            "Lựa chọn": user_choice,
                                            "Điểm": score,
                                        }
                                    )

                    if st.form_submit_button("Lưu & Cập nhật kết quả NCC này"):
                        if unanswered_questions:
                            st.error("Bạn cần chọn đầy đủ tất cả tiêu chí trước khi lưu.")
                            st.caption(
                                "Các tiêu chí chưa chọn: "
                                + "; ".join(unanswered_questions[:5])
                                + ("..." if len(unanswered_questions) > 5 else "")
                            )
                        else:
                            # Chưa gửi lên Google ngay, chỉ lưu tạm vào session.
                            # Nếu NCC này đã từng lưu thì dữ liệu mới sẽ ghi đè dữ liệu cũ.
                            replace_ncc_results(current_ncc, current_answers)
                            st.session_state.current_ncc_selector = get_next_pending_ncc(list_ncc)
                            st.rerun()
            else:
                st.warning("Site này chưa có NCC nào trong file dữ liệu.")

        if total_ncc > 0 and evaluated_count == total_ncc:
            # Khi hoàn tất toàn bộ NCC, hiện khu vực gửi dữ liệu.
            # Người dùng vẫn có thể quay lên phía trên để chọn lại một NCC và sửa kết quả.
            st.success(f"🎉 Chúc mừng! Bạn đã hoàn thành đánh giá toàn bộ {total_ncc} NCC của {selected_site}.")
            st.info(f"Số dòng chuẩn bị gửi: {len(st.session_state.all_results_buffer)}")
            st.caption("Nếu cần chỉnh lại, bạn có thể chọn lại một NCC ở phía trên rồi lưu lại trước khi gửi hệ thống.")

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
                            st.session_state.current_ncc_selector = ""
                            st.session_state.current_ncc_widget = ""
                            clear_question_widget_states()
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
