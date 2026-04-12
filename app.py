import base64
import html
import json
import os
import re
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


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


def safe_html(value):
    return html.escape(str(value or ""))


def build_logo_markup(css_class="brand-logo", fallback_text="CS"):
    logo_data_uri = get_logo_data_uri(LOGO_URL)
    if logo_data_uri:
        return f'<img src="{logo_data_uri}" alt="Cinestar logo" class="{css_class}">'
    return f'<div class="{css_class} brand-logo-fallback">{safe_html(fallback_text)}</div>'


def build_meta_tile(label, value, icon=""):
    return f"""
    <div class="meta-tile">
        <div class="meta-label">{safe_html(icon)} {safe_html(label)}</div>
        <div class="meta-value">{safe_html(value)}</div>
    </div>
    """


def build_stat_tile(label, value, detail="", tone="default"):
    return f"""
    <div class="stat-tile tone-{safe_html(tone)}">
        <div class="stat-label">{safe_html(label)}</div>
        <div class="stat-value">{safe_html(value)}</div>
        <div class="stat-detail">{safe_html(detail)}</div>
    </div>
    """


def get_local_timestamp_string():
    # Dùng giờ Việt Nam để hiển thị nhất quán trong review và dữ liệu gửi đi.
    return pd.Timestamp.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %H:%M:%S")


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
    :root {
        --bg-cream: #f7f3ff;
        --bg-soft: #fcfaff;
        --panel: rgba(255, 252, 255, 0.92);
        --panel-strong: #fffdfd;
        --border: rgba(111, 66, 193, 0.18);
        --border-strong: rgba(111, 66, 193, 0.24);
        --ink: #22324a;
        --muted: #66738d;
        --brand: #6f42c1;
        --brand-deep: #4f2f8f;
        --brand-soft: rgba(111, 66, 193, 0.10);
        --accent: #8f63dd;
        --accent-soft: rgba(143, 99, 221, 0.14);
        --shadow-lg: 0 22px 60px rgba(38, 54, 69, 0.12);
        --shadow-md: 0 14px 34px rgba(38, 54, 69, 0.08);
        --radius-xl: 28px;
        --radius-lg: 22px;
        --radius-md: 16px;
    }

    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(143, 99, 221, 0.16), transparent 28%),
            radial-gradient(circle at top right, rgba(111, 66, 193, 0.12), transparent 26%),
            linear-gradient(180deg, #fcfaff 0%, #f6f0ff 54%, #f2ebff 100%);
        color: var(--ink);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    * {
        font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    }

    h1, h2, h3, h4, h5 {
        font-family: "Segoe UI", Arial, Helvetica, sans-serif;
        letter-spacing: -0.02em;
        color: var(--brand-deep);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1240px;
        padding-top: 1.3rem !important;
        padding-bottom: 2rem !important;
    }

    [data-testid="stSidebar"] {
        background:
            radial-gradient(circle at top, rgba(143, 99, 221, 0.16), transparent 26%),
            linear-gradient(180deg, rgba(252, 250, 255, 0.98), rgba(244, 238, 255, 0.98));
        border-right: 1px solid var(--border);
    }

    .stButton>button {
        width: 100%;
        border-radius: 18px;
        height: 3.2rem;
        background: linear-gradient(135deg, var(--brand), #7f54cf 65%, var(--accent)) !important;
        color: white !important;
        font-weight: 700;
        border: none;
        box-shadow: 0 14px 28px rgba(111, 66, 193, 0.20);
        transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #5c34aa, #7d55ce 65%, #9b74e3) !important;
        color: white !important;
        transform: translateY(-1px);
        box-shadow: 0 18px 30px rgba(111, 66, 193, 0.24);
    }

    .stTextInput [data-baseweb="input"],
    .stSelectbox [data-baseweb="select"] {
        border-radius: 16px !important;
        border: 1px solid var(--border) !important;
        background: #ffffff !important;
        min-height: 3.2rem !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.75);
    }

    .stTextInput input,
    .stSelectbox input {
        font-size: 1rem !important;
        color: var(--ink) !important;
        background: #ffffff !important;
    }

    .stTextInput [data-baseweb="input"] *,
    .stSelectbox [data-baseweb="select"] * {
        background-color: transparent !important;
    }

    [data-testid="stForm"] {
        border: 1px solid var(--border-strong) !important;
        border-radius: 26px !important;
        background: #ffffff;
        box-shadow: var(--shadow-md);
        padding: 0.75rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--border) !important;
        border-radius: 24px !important;
        background: #ffffff;
        box-shadow: 0 12px 32px rgba(33, 47, 61, 0.06);
    }

    label[data-testid="stWidgetLabel"] p {
        color: var(--brand-deep);
        font-weight: 700;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 1rem 1rem 0.85rem 1rem;
        box-shadow: 0 10px 25px rgba(33, 47, 61, 0.05);
    }

    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, var(--brand), #845ad5 70%, var(--accent)) !important;
    }

    div[data-baseweb="notification"] {
        border-radius: 18px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 10px 24px rgba(33, 47, 61, 0.05);
        background: #ffffff !important;
    }

    .page-hero,
    .login-hero,
    .surface-card,
    .panel-card,
    .stat-tile,
    .meta-tile {
        animation: riseIn 0.45s ease both;
    }

    .page-hero {
        position: relative;
        overflow: hidden;
        padding: 1.9rem 2rem;
        border-radius: var(--radius-xl);
        border: 1px solid var(--border);
        background:
            radial-gradient(circle at top right, rgba(143, 99, 221, 0.16), transparent 28%),
            linear-gradient(135deg, rgba(255,255,255,0.96), rgba(244,238,255,0.92));
        box-shadow: var(--shadow-lg);
        margin-bottom: 1.1rem;
    }

    .page-hero::after {
        content: "";
        position: absolute;
        inset: auto 0 0 0;
        height: 5px;
        background: linear-gradient(90deg, var(--brand), var(--accent), var(--brand));
    }

    .hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.48rem 0.9rem;
        border-radius: 999px;
        background: var(--brand-soft);
        color: var(--brand);
        font-size: 0.88rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    .hero-title {
        margin: 0 0 0.45rem 0;
        font-size: clamp(2.15rem, 4.2vw, 3.9rem);
        line-height: 1.04;
        color: var(--brand-deep);
    }

    .hero-copy {
        margin: 0;
        max-width: 760px;
        color: var(--muted);
        font-size: 1.02rem;
        line-height: 1.8;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.95fr);
        gap: 1.3rem;
        align-items: start;
    }

    .hero-stack {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
    }

    .brand-lockup {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.85rem;
    }

    .brand-logo {
        width: 88px;
        max-width: 88px;
        border-radius: 22px;
        object-fit: contain;
        background: rgba(255,255,255,0.82);
        padding: 0.45rem;
        box-shadow: 0 14px 28px rgba(111, 66, 193, 0.12);
    }

    .brand-logo-fallback {
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.25rem;
        color: var(--brand);
    }

    .brand-mark {
        font-size: 0.92rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--accent);
        margin-bottom: 0.2rem;
    }

    .brand-name {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--brand-deep);
        font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    }

    .login-shell {
        margin: 0 auto;
        max-width: 1180px;
    }

    .login-hero,
    .surface-card,
    .panel-card {
        border-radius: var(--radius-xl);
        border: 1px solid var(--border);
        background: #ffffff;
        box-shadow: var(--shadow-lg);
        padding: 1.8rem;
    }

    .login-feature-grid,
    .meta-grid,
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.9rem;
    }

    .feature-card,
    .meta-tile,
    .stat-tile {
        border-radius: 20px;
        padding: 1rem;
        border: 1px solid var(--border);
        background: #ffffff;
    }

    .feature-title,
    .meta-label,
    .stat-label {
        font-size: 0.8rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--brand);
        margin-bottom: 0.35rem;
    }

    .feature-copy,
    .meta-value,
    .stat-detail {
        font-size: 0.95rem;
        line-height: 1.55;
        color: var(--muted);
    }

    .meta-value,
    .stat-value {
        color: var(--brand-deep);
        font-weight: 700;
        font-size: 1.02rem;
        line-height: 1.35;
    }

    .stat-value {
        font-size: 1.9rem;
        line-height: 1;
        margin-bottom: 0.35rem;
        font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    }

    .tone-progress {
        background: linear-gradient(180deg, rgba(18,59,93,0.07), rgba(255,255,255,0.86));
    }

    .tone-ready {
        background: linear-gradient(180deg, rgba(198,122,31,0.12), rgba(255,255,255,0.88));
    }

    .tone-neutral {
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(244,238,255,0.9));
    }

    .section-eyebrow {
        color: var(--accent);
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
    }

    .section-heading {
        margin: 0 0 0.4rem 0;
        font-size: 1.8rem;
        color: var(--brand-deep);
    }

    .section-copy {
        margin: 0;
        color: var(--muted);
        line-height: 1.7;
        font-size: 0.97rem;
    }

    .inline-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-top: 0.65rem;
    }

    .legend-chip {
        padding: 0.4rem 0.8rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.78);
        color: var(--muted);
        font-size: 0.86rem;
        font-weight: 600;
    }

    .legend-chip strong {
        color: var(--brand-deep);
    }

    .page-note {
        margin-top: 0.45rem;
        color: var(--muted);
        font-size: 0.93rem;
        line-height: 1.65;
    }

    .compact-actions {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
    }

    .question-stage-title {
        margin: 0.1rem 0 0.3rem 0;
        color: var(--brand-deep);
        font-size: 2rem;
    }

    .question-stage-subtitle {
        margin: 0;
        color: var(--muted);
        line-height: 1.65;
    }

    @keyframes riseIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] {
            padding-top: 1rem !important;
            padding-bottom: 1.5rem !important;
        }

        [data-testid="stHorizontalBlock"] {
            flex-direction: column;
            gap: 0.9rem;
        }

        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        .page-hero,
        .login-hero,
        .surface-card,
        .panel-card {
            padding: 1.25rem;
            border-radius: 24px;
        }

        .hero-grid,
        .login-feature-grid,
        .meta-grid,
        .stat-grid {
            grid-template-columns: 1fr;
        }

        .hero-title {
            font-size: clamp(1.9rem, 8vw, 2.6rem);
        }

        .brand-lockup {
            align-items: flex-start;
        }

        .brand-logo {
            width: 72px;
            max-width: 72px;
            border-radius: 18px;
        }
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
if "login_site_widget" not in st.session_state:
    st.session_state.login_site_widget = "-- Chọn Site --"
if "selected_dept" not in st.session_state:
    st.session_state.selected_dept = "-- Chọn Bộ phận --"
if "login_dept_widget" not in st.session_state:
    st.session_state.login_dept_widget = "-- Chọn Bộ phận --"
if "evaluator_name" not in st.session_state:
    st.session_state.evaluator_name = ""
if "evaluator_name_widget" not in st.session_state:
    st.session_state.evaluator_name_widget = st.session_state.evaluator_name
if "current_ncc_selector" not in st.session_state:
    st.session_state.current_ncc_selector = ""
if "current_ncc_widget" not in st.session_state:
    st.session_state.current_ncc_widget = ""
if "pending_ncc_widget_value" not in st.session_state:
    st.session_state.pending_ncc_widget_value = ""
if "scroll_to_top" not in st.session_state:
    st.session_state.scroll_to_top = False
if "evaluated_nccs" not in st.session_state:
    st.session_state.evaluated_nccs = []
if "all_results_buffer" not in st.session_state:
    st.session_state.all_results_buffer = []
if "last_api_status" not in st.session_state:
    st.session_state.last_api_status = None
if "last_api_response" not in st.session_state:
    st.session_state.last_api_response = None
if "confirm_submit_results" not in st.session_state:
    st.session_state.confirm_submit_results = False
if "edited_nccs" not in st.session_state:
    st.session_state.edited_nccs = []
if "last_saved_ncc" not in st.session_state:
    st.session_state.last_saved_ncc = ""


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


def normalize_department_label(value):
    # Chuẩn hóa tên bộ phận để so khớp ổn định giữa các file Excel.
    return " ".join(str(value).replace("\n", " ").split()).strip()


def get_department_options(df_depts):
    # Dropdown bộ phận phải lấy từ file danh sách bộ phận đánh giá.
    if df_depts.empty:
        return ["-- Chọn Bộ phận --"]

    dept_options = [
        normalize_department_label(value)
        for value in df_depts.iloc[:, 0].dropna().tolist()
        if normalize_department_label(value)
    ]
    return ["-- Chọn Bộ phận --"] + list(dict.fromkeys(dept_options))


def parse_departments_from_question_cell(value):
    # Trong file câu hỏi, một ô có thể chứa nhiều bộ phận,
    # mỗi bộ phận nằm trong dấu "" và cách nhau bằng dấu phẩy.
    cell_text = str(value or "").replace("\n", " ").strip()
    if not cell_text:
        return []

    quoted_departments = re.findall(r'"([^"]+)"', cell_text)
    if quoted_departments:
        return [
            normalize_department_label(item)
            for item in quoted_departments
            if normalize_department_label(item)
        ]

    # Fallback cho các dòng không có dấu " nhưng vẫn chứa dữ liệu cũ.
    return [
        normalize_department_label(item)
        for item in cell_text.split(",")
        if normalize_department_label(item)
    ]


def question_matches_department(question_dept_value, selected_dept):
    # So khớp tuyệt đối theo từng bộ phận được khai báo trong ô câu hỏi.
    normalized_selected_dept = normalize_department_label(selected_dept).casefold()
    parsed_departments = parse_departments_from_question_cell(question_dept_value)
    return any(dept.casefold() == normalized_selected_dept for dept in parsed_departments)


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

    was_already_saved = ncc_name in st.session_state.evaluated_nccs

    if not was_already_saved:
        st.session_state.evaluated_nccs.append(ncc_name)
    elif ncc_name not in st.session_state.edited_nccs:
        st.session_state.edited_nccs.append(ncc_name)

    # Khi có thay đổi dữ liệu, cần xác nhận lại trước khi gửi toàn bộ kết quả.
    st.session_state.confirm_submit_results = False
    st.session_state.last_api_status = None
    st.session_state.last_api_response = None
    st.session_state.last_saved_ncc = ncc_name


def clear_question_widget_states():
    # Xóa các widget câu hỏi sau khi gửi thành công
    # để phiên đánh giá mới không bị giữ lại đáp án cũ.
    for key in list(st.session_state.keys()):
        if str(key).startswith("q_"):
            del st.session_state[key]


def scroll_page_to_top():
    # Sau khi lưu một NCC hoặc chuyển trang review, cuộn về đầu trang
    # để người dùng tiếp tục thao tác ở khu vực điều hướng chính.
    components.html(
        """
        <script>
        const targetWindow = window.parent || window;
        const targetDocument = targetWindow.document || document;

        function resetScrollPosition() {
            const scrollTargets = [
                targetWindow,
                targetDocument.documentElement,
                targetDocument.body,
                targetDocument.scrollingElement,
                targetDocument.querySelector('[data-testid="stAppViewContainer"]'),
                targetDocument.querySelector('section.main'),
                targetDocument.querySelector('[data-testid="stMain"]'),
            ].filter(Boolean);

            scrollTargets.forEach((target) => {
                try {
                    if (typeof target.scrollTo === "function") {
                        target.scrollTo({ top: 0, left: 0, behavior: "instant" });
                    }
                } catch (error) {}
                try {
                    target.scrollTop = 0;
                    target.scrollLeft = 0;
                } catch (error) {}
            });
        }

        resetScrollPosition();
        [60, 180, 360, 720].forEach((delay) => {
            targetWindow.setTimeout(resetScrollPosition, delay);
        });
        </script>
        """,
        height=0,
    )


def bind_enter_to_button(button_text, binding_key):
    # Cho phép nhấn Enter để kích hoạt nút hành động chính ở một số màn hình.
    escaped_button_text = json.dumps(button_text)
    escaped_binding_key = json.dumps(binding_key)
    components.html(
        f"""
        <script>
        const targetWindow = window.parent || window;
        if (targetWindow && !targetWindow.__codexEnterBindings) {{
            targetWindow.__codexEnterBindings = {{}};
        }}
        if (targetWindow && !targetWindow.__codexEnterBindings[{escaped_binding_key}]) {{
            targetWindow.__codexEnterBindings[{escaped_binding_key}] = true;
            targetWindow.document.addEventListener("keydown", function(event) {{
                const active = targetWindow.document.activeElement;
                const tagName = active ? active.tagName : "";
                const inputType = active ? (active.getAttribute("type") || "") : "";
                if (event.key !== "Enter" || event.shiftKey) {{
                    return;
                }}
                if (tagName === "TEXTAREA" || inputType === "text" || inputType === "password") {{
                    return;
                }}
                const buttons = Array.from(targetWindow.document.querySelectorAll("button"));
                const matchedButton = buttons.find((button) => button.innerText.trim() === {escaped_button_text});
                if (matchedButton && !matchedButton.disabled) {{
                    event.preventDefault();
                    matchedButton.click();
                }}
            }});
        }}
        </script>
        """,
        height=0,
    )


def reset_evaluation_flow():
    # Làm sạch toàn bộ dữ liệu tạm của một phiên đánh giá
    # nhưng vẫn giữ lại site và bộ phận đang đăng nhập.
    st.session_state.evaluated_nccs = []
    st.session_state.edited_nccs = []
    st.session_state.all_results_buffer = []
    st.session_state.current_ncc_selector = ""
    st.session_state.current_ncc_widget = ""
    st.session_state.pending_ncc_widget_value = ""
    st.session_state.confirm_submit_results = False
    st.session_state.last_api_status = None
    st.session_state.last_api_response = None
    st.session_state.evaluator_name = ""
    st.session_state.evaluator_name_widget = ""
    st.session_state.scroll_to_top = False
    st.session_state.last_saved_ncc = ""
    clear_question_widget_states()


def build_review_summary_df(rows):
    # Tạo bảng tóm tắt theo từng NCC để trang review dễ kiểm tra hơn.
    if not rows:
        return pd.DataFrame()

    summary_df = (
        pd.DataFrame(rows)
        .groupby("Tên NCC", as_index=False)
        .agg(
            **{
                "Số tiêu chí": ("Tiêu chí", "count"),
                "Tổng điểm": ("Điểm", "sum"),
            }
        )
    )
    summary_df["Tổng điểm"] = summary_df["Tổng điểm"].astype(float).round(2)
    return summary_df


def get_saved_answers_map(site_name, dept_name, ncc_name):
    # Lấy lại các đáp án đã lưu trước đó của đúng site/bộ phận/NCC
    # để khi mở lại NCC, form có thể hiển thị sẵn lựa chọn cũ.
    saved_rows = [
        row
        for row in st.session_state.all_results_buffer
        if row.get("Site") == site_name
        and row.get("Bộ phận") == dept_name
        and row.get("Tên NCC") == ncc_name
    ]
    return {
        (str(row.get("Nhóm", "")), str(row.get("Tiêu chí", ""))): str(row.get("Lựa chọn", ""))
        for row in saved_rows
    }


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


def format_ncc_status_label(ncc_name, evaluated_nccs_for_site):
    # Streamlit selectbox không hỗ trợ tô màu từng option như HTML custom,
    # nên dùng emoji màu để đồng bộ trạng thái trong dropdown.
    if ncc_name in st.session_state.edited_nccs:
        return f"🟠 Đã chỉnh sửa | {ncc_name}"
    if ncc_name in evaluated_nccs_for_site:
        return f"🟢 Đã lưu | {ncc_name}"
    return f"🟡 Chưa hoàn tất | {ncc_name}"


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
        [data-testid="stAppViewContainer"] { overflow: hidden !important; }
        [data-testid="stMainBlockContainer"] {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        @media (max-width: 900px) {
            [data-testid="stAppViewContainer"] { overflow: auto !important; }
            [data-testid="stMainBlockContainer"] {
                min-height: auto;
                display: block;
            }
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    df_sites_login, df_depts_login, _ = load_input_files()
    site_options = ["-- Chọn Site --"] + (df_sites_login["Site"].dropna().unique().tolist() if not df_sites_login.empty else [])
    dept_options_login = get_department_options(df_depts_login)
    if st.session_state.login_site_widget not in site_options:
        st.session_state.login_site_widget = st.session_state.selected_site
    if st.session_state.login_site_widget not in site_options:
        st.session_state.login_site_widget = "-- Chọn Site --"
    if st.session_state.login_dept_widget not in dept_options_login:
        st.session_state.login_dept_widget = st.session_state.selected_dept
    if st.session_state.login_dept_widget not in dept_options_login:
        st.session_state.login_dept_widget = "-- Chọn Bộ phận --"

    logo_markup = build_logo_markup("brand-logo", "CS")
    left_col, right_col = st.columns([1.2, 0.92])

    with left_col:
        st.markdown(
            f"""
            <div class="login-hero">
                <div class="hero-kicker">Cổng khảo sát nội bộ</div>
                <div class="brand-lockup">
                    {logo_markup}
                    <div>
                        <div class="brand-mark">Cinestar Vendor Review</div>
                        <div class="brand-name">Đánh giá NCC theo từng site</div>
                    </div>
                </div>
                <h1 class="hero-title">Đăng nhập một lần, hoàn tất cả phiên đánh giá.</h1>
                <p class="hero-copy">
                    Hệ thống được thiết kế để từng bộ phận đánh giá đúng nhóm câu hỏi của mình,
                    đồng thời chỉ hiển thị đúng danh sách nhà cung cấp thuộc site đang đăng nhập.
                </p>
                <div class="login-feature-grid" style="margin-top: 1.2rem;">
                    <div class="feature-card">
                        <div class="feature-title">Phân quyền đơn giản</div>
                        <div class="feature-copy">Chọn đúng site và bộ phận để hệ thống mở đúng phạm vi khảo sát.</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-title">Đánh giá có kiểm soát</div>
                        <div class="feature-copy">Mỗi NCC được lưu riêng, có thể quay lại chỉnh sửa trước khi nộp chính thức.</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-title">Tối ưu cho di động</div>
                        <div class="feature-copy">Giao diện gọn, nút bấm lớn, thao tác dễ dùng trên desktop lẫn điện thoại.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        with st.container(border=True):
            st.markdown(
                """
                <div class="section-eyebrow">Bước 1</div>
                <h3 class="section-heading">Thông tin truy cập</h3>
                <p class="section-copy">
                    Chọn site, bộ phận đánh giá và nhập mật khẩu tương ứng để bắt đầu phiên khảo sát.
                </p>
                """,
                unsafe_allow_html=True,
            )

            with st.form("login_form", clear_on_submit=False):
                login_site = st.selectbox("🏢 Chọn Site", site_options, key="login_site_widget")
                login_dept = st.selectbox("📁 Chọn Bộ phận", dept_options_login, key="login_dept_widget")
                pwd = st.text_input("🔑 Mật khẩu truy cập", type="password")
                submit_login = st.form_submit_button("ĐĂNG NHẬP VÀO HỆ THỐNG", use_container_width=True)

            if submit_login:
                if login_site == "-- Chọn Site --":
                    st.error("Vui lòng chọn Site trước khi đăng nhập.")
                elif login_dept == "-- Chọn Bộ phận --":
                    st.error("Vui lòng chọn Bộ phận trước khi đăng nhập.")
                elif pwd == build_site_password(login_site):
                    st.session_state.selected_site = login_site
                    st.session_state.selected_dept = normalize_department_label(login_dept)
                    st.session_state.current_page = "welcome"
                    st.rerun()
                else:
                    st.error("Sai mật khẩu. Vui lòng kiểm tra lại thông tin đăng nhập.")

            st.markdown(
                """
                <p class="page-note">
                    Mật khẩu đang được kiểm tra theo từng site. Sau khi đăng nhập thành công,
                    bạn chỉ cần nhập tên nhân viên và bắt đầu đánh giá.
                </p>
                """,
                unsafe_allow_html=True,
            )


# =====================================================================
# TRANG 2: LỜI CHÀO MỪNG
# - hiển thị nội dung giới thiệu
# - có nút để chuyển sang trang đánh giá
# =====================================================================
elif st.session_state.current_page == "welcome":
    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"] {
            padding-top: 1rem !important;
            padding-bottom: 1.5rem !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    current_site = st.session_state.selected_site or "Site đã chọn"
    logo_markup = build_logo_markup("brand-logo", "CS")
    left_col, right_col = st.columns([1.8, 1])

    with left_col:
        st.markdown(
            f"""
            <div class="page-hero">
                <div class="hero-kicker">Khởi động phiên đánh giá</div>
                <div class="brand-lockup">
                    {logo_markup}
                    <div>
                        <div class="brand-mark">Cinestar Cinemas Vietnam</div>
                        <div class="brand-name">Khảo sát đánh giá Nhà cung cấp</div>
                    </div>
                </div>
                <h1 class="hero-title">Hãy để người trải nghiệm trực tiếp lên tiếng.</h1>
                <p class="hero-copy">
                    Chào mừng bạn đến với hệ thống đánh giá chất lượng nhà cung cấp định kỳ.
                    Mọi ý kiến của bạn là cơ sở để công ty nhìn nhận đúng năng lực đối tác,
                    từ đó nâng cao chất lượng dịch vụ và tối ưu hóa vận hành tại từng site.
                </p>
                <p class="page-note">
                    Hoàn thành khảo sát với góc nhìn thực tế, khách quan và đầy đủ nhất để kết quả phản ánh đúng chất lượng hợp tác.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(build_meta_tile("Site đăng nhập", current_site, "🏢"), unsafe_allow_html=True)
        st.markdown(build_meta_tile("Bộ phận đánh giá", st.session_state.selected_dept or "--", "📁"), unsafe_allow_html=True)
        st.markdown(build_meta_tile("Phạm vi khảo sát", "Danh sách NCC theo site đã đăng nhập", "🎯"), unsafe_allow_html=True)
        st.markdown(
            """
            <div class="panel-card" style="padding: 1.15rem;">
                <div class="feature-title">Mục tiêu phiên khảo sát</div>
                <div class="feature-copy">
                    Đánh giá định kỳ để cải thiện chất lượng dịch vụ, tiến độ cung ứng
                    và mức độ phối hợp với từng nhà cung cấp.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="surface-card" style="margin-top: 0.9rem;">
            <div class="section-eyebrow">Sẵn sàng bắt đầu?</div>
            <h3 class="section-heading">Chuyển sang khu vực đánh giá chi tiết</h3>
            <p class="section-copy">
                Ở bước tiếp theo, bạn sẽ chọn từng NCC trong site hiện tại, hoàn tất đánh giá
                theo đúng bộ phận và lưu kết quả trước khi review lần cuối.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

    st.markdown(
        f"""
        <div class="page-hero">
            <div class="hero-kicker">Bước 2 · Đánh giá chi tiết</div>
            <h1 class="hero-title">Bảng đánh giá nhà cung cấp</h1>
            <p class="hero-copy">
                Hoàn tất lần lượt từng NCC trong site <strong>{safe_html(st.session_state.selected_site or "--")}</strong>,
                với bộ câu hỏi dành riêng cho bộ phận <strong>{safe_html(st.session_state.selected_dept or "--")}</strong>.
                Hệ thống sẽ lưu tạm từng NCC để bạn review lại trước khi nộp chính thức.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.scroll_to_top:
        scroll_page_to_top()
        st.session_state.scroll_to_top = False

    if not st.session_state.selected_site:
        st.warning("Chưa có Site đăng nhập. Vui lòng quay lại màn hình đăng nhập.")
        st.session_state.current_page = "login"
        st.rerun()

    # Nếu chưa có WEB_APP_URL thì vẫn có thể thao tác,
    # nhưng chưa thể gửi dữ liệu lên Google Sheet.
    if not WEB_APP_URL:
        st.warning("Chưa cấu hình WEB_APP_URL trong Streamlit secrets nên chưa thể gửi dữ liệu lên Google Sheet.")

    df_sites, _, df_questions = load_input_files()

    with st.container(border=True):
        st.markdown(
            """
            <div class="section-eyebrow">Thông tin phiên làm việc</div>
            <h3 class="section-heading">Xác nhận người thực hiện đánh giá</h3>
            <p class="section-copy">
                Chỉ cần nhập tên nhân viên. Site và bộ phận đã được cố định từ bước đăng nhập
                để đảm bảo mỗi người đánh giá đúng bộ câu hỏi của mình.
            </p>
            """,
            unsafe_allow_html=True,
        )

        evaluator_name = st.text_input("👤 Họ tên nhân viên đánh giá", key="evaluator_name_widget")
        st.session_state.evaluator_name = evaluator_name
        meta_col1, meta_col2 = st.columns(2)
        meta_col1.info(f"🏢 Site đăng nhập: {st.session_state.selected_site}")
        meta_col2.info(f"📁 Bộ phận đánh giá: {st.session_state.selected_dept}")

    selected_site = st.session_state.selected_site
    selected_dept = st.session_state.selected_dept

    if selected_site and selected_dept != "-- Chọn Bộ phận --" and evaluator_name.strip():
        # Lấy danh sách NCC của site đang chọn
        list_ncc = df_sites[df_sites["Site"] == selected_site]["NCC"].dropna().tolist()
        total_ncc = len(list_ncc)
        evaluated_nccs_for_site = [ncc for ncc in list_ncc if ncc in set(st.session_state.evaluated_nccs)]
        evaluated_count = len(evaluated_nccs_for_site)

        st.divider()
        if list_ncc:
            remaining_count = total_ncc - evaluated_count
            if st.session_state.last_saved_ncc:
                st.success(
                    f"Đã lưu xong NCC: {st.session_state.last_saved_ncc}. Bạn có thể tiếp tục NCC tiếp theo hoặc chỉnh lại nếu cần."
                )

            stat_tiles_markup = "".join(
                [
                    build_stat_tile("Tổng NCC", total_ncc, "Danh sách của site hiện tại", "neutral"),
                    build_stat_tile("Đã hoàn tất", evaluated_count, "Các NCC đã được lưu", "progress"),
                    build_stat_tile(
                        "Còn lại",
                        remaining_count,
                        "Tiếp tục lần lượt cho đến khi đủ toàn bộ",
                        "ready" if remaining_count == 0 else "neutral",
                    ),
                ]
            )

            st.markdown(
                f"""
                <div class="surface-card">
                    <div class="section-eyebrow">Tiến độ phiên đánh giá</div>
                    <h3 class="section-heading">Theo dõi nhanh trạng thái hoàn tất</h3>
                    <p class="section-copy">
                        NCC tiếp theo được gợi ý: <strong>{safe_html(get_next_pending_ncc(list_ncc))}</strong>.
                        Bạn có thể chọn lại NCC đã lưu để cập nhật trước khi nộp.
                    </p>
                    <div class="stat-grid" style="margin-top: 1rem;">{stat_tiles_markup}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(evaluated_count / total_ncc if total_ncc > 0 else 0)
            if total_ncc > 0 and evaluated_count == total_ncc:
                st.success("Toàn bộ NCC đã được đánh giá xong. Bạn có thể chỉnh lại nếu cần, hoặc chuyển sang bước nộp kết quả.")
                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    st.info("Nếu không cần chỉnh sửa thêm, hãy qua trang nộp kết quả.")
                with action_col2:
                    if st.button("🔍 Qua trang review & nộp kết quả", type="primary", use_container_width=True):
                        st.session_state.confirm_submit_results = False
                        st.session_state.current_page = "review_submit"
                        st.session_state.scroll_to_top = True
                        st.rerun()
            else:
                st.info(f"Còn {remaining_count} NCC cần đánh giá trước khi mở bước review cuối.")

            # Tự động trỏ tới NCC chưa hoàn thành tiếp theo để thao tác nhanh hơn.
            if st.session_state.current_ncc_selector not in list_ncc:
                st.session_state.current_ncc_selector = get_next_pending_ncc(list_ncc)
            if st.session_state.pending_ncc_widget_value in list_ncc:
                st.session_state.current_ncc_selector = st.session_state.pending_ncc_widget_value
                st.session_state.current_ncc_widget = st.session_state.pending_ncc_widget_value
                st.session_state.pending_ncc_widget_value = ""
            elif st.session_state.current_ncc_widget not in list_ncc:
                st.session_state.current_ncc_widget = st.session_state.current_ncc_selector

            # Chỉ giữ dropdown chọn NCC, không hiển thị danh sách NCC riêng bên cạnh.
            current_ncc = st.selectbox(
                "👉 Chọn NCC để đánh giá hoặc đánh giá lại:",
                list_ncc,
                key="current_ncc_widget",
                format_func=lambda ncc: format_ncc_status_label(ncc, evaluated_nccs_for_site),
            )
            st.session_state.current_ncc_selector = current_ncc
            st.markdown(
                """
                <div class="inline-legend">
                    <span class="legend-chip"><strong>🟡</strong> Chưa hoàn tất</span>
                    <span class="legend-chip"><strong>🟢</strong> Đã lưu</span>
                    <span class="legend-chip"><strong>🟠</strong> Đã chỉnh sửa</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if current_ncc in evaluated_nccs_for_site:
                st.info("NCC này đã được lưu trước đó. Nếu bạn chỉnh lại và bấm lưu, hệ thống sẽ thay kết quả cũ bằng kết quả mới.")
            if current_ncc in st.session_state.edited_nccs:
                st.caption("✏️ Đã chỉnh sửa: NCC này đã được cập nhật lại sau lần lưu đầu tiên.")

            with st.container(border=True):
                # Lọc câu hỏi đúng với bộ phận mà người dùng đã chọn
                st.markdown(
                    f"""
                    <div class="section-eyebrow">Biểu mẫu đánh giá</div>
                    <h3 class="question-stage-title">{safe_html(current_ncc)}</h3>
                    <p class="question-stage-subtitle">
                        Hoàn tất tất cả tiêu chí bên dưới để lưu NCC này. Điểm sẽ cập nhật ngay khi bạn chọn đáp án.
                    </p>
                    """,
                    unsafe_allow_html=True,
                )
                df_q_filtered = df_questions[
                    df_questions["Câu hỏi dành cho bộ phận"].map(
                        lambda value: question_matches_department(value, selected_dept)
                    )
                ]
                saved_answers_map = get_saved_answers_map(selected_site, selected_dept, current_ncc)
                current_answers = []
                unanswered_questions = []

                if df_q_filtered.empty:
                    st.warning("Bộ phận của bạn chưa có bộ câu hỏi khảo sát.")
                else:
                    # Hiển thị theo từng Nhóm.
                    # Trong mỗi Nhóm sẽ liệt kê toàn bộ câu hỏi/tiêu chí của nhóm đó.
                    for group_name, group_df in df_q_filtered.groupby("Nhóm", sort=False):
                        with st.container(border=True):
                            st.markdown(f"### {group_name}")

                            criteria_in_group = list(dict.fromkeys(group_df["Tiêu chí"].dropna().astype(str).tolist()))

                            for criterion in criteria_in_group:
                                st.markdown(f"**{criterion}**")
                                options_df = group_df[group_df["Tiêu chí"].astype(str) == criterion].copy()
                                choice_options = list(dict.fromkeys(options_df["Lựa chọn"].dropna().astype(str).tolist()))
                                question_key = f"q_{selected_dept}_{group_name}_{criterion}_{current_ncc}"

                                if not choice_options:
                                    st.warning(f"Tiêu chí '{criterion}' hiện chưa có lựa chọn đánh giá trong file Excel.")
                                    unanswered_questions.append(f"{group_name} - {criterion}")
                                    continue

                                saved_choice = saved_answers_map.get((str(group_name), str(criterion)))
                                if question_key not in st.session_state and saved_choice in choice_options:
                                    st.session_state[question_key] = saved_choice

                                user_choice = st.radio(
                                    "Chọn mức đánh giá",
                                    choice_options,
                                    key=question_key,
                                    index=None,
                                    label_visibility="collapsed",
                                )

                                if user_choice is None:
                                    unanswered_questions.append(f"{group_name} - {criterion}")
                                else:
                                    score_series = options_df.loc[
                                        options_df["Lựa chọn"].astype(str) == str(user_choice), "Điểm"
                                    ]
                                    if score_series.empty:
                                        unanswered_questions.append(f"{group_name} - {criterion}")
                                        continue
                                    score_raw = score_series.iloc[0]
                                    score = float(score_raw)
                                    current_answers.append(
                                        {
                                            "Thời gian": "",
                                            "Họ tên NV đánh giá": evaluator_name.strip(),
                                            "Bộ phận": selected_dept,
                                            "Site": selected_site,
                                            "Tên NCC": current_ncc,
                                            "Nhóm": group_name,
                                            "Tiêu chí": criterion,
                                            "Lựa chọn": user_choice,
                                            "Điểm": score,
                                        }
                                    )

                if current_answers:
                    total_temp_score = sum(float(answer["Điểm"]) for answer in current_answers)
                    answered_count = len(current_answers)
                    st.info(
                        f"📊 Tổng điểm hiện tại của NCC này: {total_temp_score:.2f} điểm | Đã chọn {answered_count} tiêu chí"
                    )
                else:
                    st.caption("📊 Tổng điểm sẽ hiển thị ngay khi bạn bắt đầu chọn các tiêu chí đánh giá.")

                bind_enter_to_button("Lưu & Cập nhật kết quả NCC này", f"save-{current_ncc}")
                if st.button("Lưu & Cập nhật kết quả NCC này", key=f"save_{current_ncc}", use_container_width=True):
                    if unanswered_questions:
                        st.error("Bạn cần chọn đầy đủ tất cả tiêu chí trước khi lưu.")
                        st.caption(
                            "Các tiêu chí chưa chọn: "
                            + "; ".join(unanswered_questions[:5])
                            + ("..." if len(unanswered_questions) > 5 else "")
                        )
                    else:
                        saved_timestamp = get_local_timestamp_string()
                        answers_to_save = [{**answer, "Thời gian": saved_timestamp} for answer in current_answers]
                        replace_ncc_results(current_ncc, answers_to_save)
                        next_ncc = get_next_pending_ncc(list_ncc)
                        st.session_state.current_ncc_selector = next_ncc
                        st.session_state.pending_ncc_widget_value = next_ncc
                        st.session_state.scroll_to_top = True
                        st.rerun()
        else:
            st.warning("Site này chưa có NCC nào trong file dữ liệu.")
    else:
        st.info("Điền họ tên nhân viên để hệ thống hiển thị form đánh giá theo đúng bộ phận đã đăng nhập.")


elif st.session_state.current_page == "review_submit":
    try:
        st.sidebar.image(LOGO_URL, use_container_width=True)
    except Exception:
        pass

    st.sidebar.divider()
    if st.sidebar.button("🚪 Thoát (Đăng xuất)"):
        st.session_state.clear()
        st.rerun()

    st.markdown(
        f"""
        <div class="page-hero">
            <div class="hero-kicker">Bước 3 · Review & Submit</div>
            <h1 class="hero-title">Kiểm tra lần cuối trước khi nộp</h1>
            <p class="hero-copy">
                Đây là bước xác nhận cuối cùng cho site <strong>{safe_html(st.session_state.selected_site or "--")}</strong>
                và bộ phận <strong>{safe_html(st.session_state.selected_dept or "--")}</strong>. Hãy rà lại toàn bộ
                dữ liệu trước khi gửi chính thức vào hệ thống.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.scroll_to_top:
        scroll_page_to_top()
        st.session_state.scroll_to_top = False

    if not st.session_state.selected_site:
        st.warning("Chưa có Site đăng nhập. Vui lòng quay lại màn hình đăng nhập.")
        st.session_state.current_page = "login"
        st.rerun()

    if not WEB_APP_URL:
        st.warning("Chưa cấu hình WEB_APP_URL trong Streamlit secrets nên chưa thể gửi dữ liệu lên Google Sheet.")

    df_sites, _, _ = load_input_files()
    selected_site = st.session_state.selected_site
    list_ncc = df_sites[df_sites["Site"] == selected_site]["NCC"].dropna().tolist()
    total_ncc = len(list_ncc)
    evaluated_nccs_for_site = [ncc for ncc in list_ncc if ncc in set(st.session_state.evaluated_nccs)]
    evaluated_count = len(evaluated_nccs_for_site)

    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        if st.button("⬅️ Quay lại trang 3 để đánh giá lại", use_container_width=True):
            st.session_state.evaluator_name_widget = st.session_state.get("evaluator_name", "")
            st.session_state.pending_ncc_widget_value = st.session_state.get("current_ncc_selector", "")
            st.session_state.current_page = "evaluation"
            st.session_state.scroll_to_top = True
            st.rerun()
    with top_col2:
        st.markdown(
            """
            <div class="panel-card" style="padding: 1rem 1.1rem;">
                <div class="feature-title">Trạng thái hiện tại</div>
                <div class="feature-copy">Trang review đã sẵn sàng cho bước xác nhận nộp kết quả.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if total_ncc == 0:
        st.warning("Site này chưa có NCC nào trong file dữ liệu.")
    elif evaluated_count < total_ncc:
        st.warning("Bạn chưa hoàn thành toàn bộ danh sách NCC nên chưa thể nộp kết quả.")
    elif not st.session_state.all_results_buffer:
        st.warning("Chưa có dữ liệu đánh giá để review.")
    else:
        review_df = pd.DataFrame(st.session_state.all_results_buffer)
        summary_df = build_review_summary_df(st.session_state.all_results_buffer)
        summary_tiles_markup = "".join(
            [
                build_stat_tile("Site", selected_site, "Phạm vi nhà cung cấp đang nộp", "neutral"),
                build_stat_tile("Bộ phận", st.session_state.selected_dept, "Bộ câu hỏi đã sử dụng", "progress"),
                build_stat_tile("Số NCC", f"{evaluated_count}/{total_ncc}", "Tất cả NCC đã hoàn tất", "ready"),
            ]
        )

        st.markdown(
            f"""
            <div class="surface-card">
                <div class="section-eyebrow">Tổng hợp phiên nộp</div>
                <h3 class="section-heading">Thông tin xác nhận</h3>
                <p class="section-copy">
                    Người đánh giá: <strong>{safe_html(st.session_state.evaluator_name)}</strong>.
                    Tổng số dòng dữ liệu chuẩn bị gửi: <strong>{safe_html(len(review_df))}</strong>.
                </p>
                <div class="stat-grid" style="margin-top: 1rem;">{summary_tiles_markup}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Tổng hợp theo NCC")
        with st.container(border=True):
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True,
                height=min(320, 42 * (len(summary_df) + 1)),
                column_config={
                    "Tên NCC": st.column_config.TextColumn(width="large"),
                    "Số tiêu chí": st.column_config.NumberColumn(width="small"),
                    "Tổng điểm": st.column_config.NumberColumn(format="%.2f", width="small"),
                },
            )

        st.markdown("### Chi tiết đánh giá")
        detail_ncc_options = summary_df["Tên NCC"].astype(str).tolist()
        if "review_detail_ncc" in st.session_state and st.session_state.review_detail_ncc not in detail_ncc_options:
            del st.session_state["review_detail_ncc"]
        with st.container(border=True):
            detail_selected_ncc = st.selectbox(
                "Chọn NCC để xem chi tiết",
                detail_ncc_options,
                key="review_detail_ncc",
            )
            detail_df = review_df[review_df["Tên NCC"].astype(str) == str(detail_selected_ncc)].copy()
            detail_df = detail_df[["Thời gian", "Nhóm", "Tiêu chí", "Lựa chọn", "Điểm"]]
            st.dataframe(
                detail_df,
                use_container_width=True,
                hide_index=True,
                height=min(360, 42 * (len(detail_df) + 1)),
                column_config={
                    "Thời gian": st.column_config.TextColumn(width="medium"),
                    "Nhóm": st.column_config.TextColumn(width="medium"),
                    "Tiêu chí": st.column_config.TextColumn(width="large"),
                    "Lựa chọn": st.column_config.TextColumn(width="large"),
                    "Điểm": st.column_config.NumberColumn(format="%.2f", width="small"),
                },
            )

        st.markdown(
            """
            <div class="panel-card" style="margin-top: 0.9rem;">
                <div class="feature-title">Xác nhận nộp dữ liệu</div>
                <div class="feature-copy">
                    Sau khi xác nhận nộp, dữ liệu sẽ được gửi lên hệ thống. Nếu cần chỉnh sửa,
                    hãy quay lại bước đánh giá trước khi bấm nút xác nhận cuối cùng.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.checkbox(
            "Tôi đã review xong và muốn nộp toàn bộ kết quả vào hệ thống.",
            key="confirm_submit_results",
        )

        bind_enter_to_button("🚀 XÁC NHẬN NỘP KẾT QUẢ", "submit-review")
        if st.button(
            "🚀 XÁC NHẬN NỘP KẾT QUẢ",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state.confirm_submit_results,
        ):
            with st.spinner("Đang truyền dữ liệu bảo mật..."):
                try:
                    # Gửi dữ liệu sang Google Apps Script
                    response, _ = send_results_to_google_sheet(st.session_state.all_results_buffer)

                    # Ghi lại phản hồi để tiện kiểm tra khi có lỗi
                    st.session_state.last_api_status = response.status_code
                    st.session_state.last_api_response = response.text

                    if response.status_code == 200:
                        st.balloons()
                        st.success("✅ Dữ liệu đã được gửi thành công tới Web App.")
                        reset_evaluation_flow()
                        st.session_state.current_page = "welcome"
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

        if st.session_state.last_api_status is not None and st.session_state.last_api_status != 200:
            # Khu debug phản hồi lần gửi gần nhất
            st.write(f"Status code lần gửi gần nhất: {st.session_state.last_api_status}")
            st.code(st.session_state.last_api_response or "(response rỗng)")
