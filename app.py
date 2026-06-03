import streamlit as st
import json
import re
import os
import html
import pandas as pd
from io import BytesIO

# ---------- Cấu hình ----------
KEYWORD_FILE = "keywords.json"
WEB_OPTIONS = ["Thế Giới Di Động", "Điện Máy Xanh", "TopZone"]

st.set_page_config(page_title="Công cụ chèn Link", layout="wide")

# ---------- Quản lý Session State ----------
if "keywords" not in st.session_state:
    st.session_state.keywords = {w: {} for w in WEB_OPTIONS}
if "paragraphs" not in st.session_state:
    st.session_state.paragraphs = []
if "is_h3" not in st.session_state:
    st.session_state.is_h3 = []

# ---------- Load / Lưu từ khóa ----------
def load_keywords():
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for w in WEB_OPTIONS:
                        if w not in data:
                            data[w] = {}
                    return data
        except:
            pass
    return {w: {} for w in WEB_OPTIONS}

def save_keywords():
    try:
        with open(KEYWORD_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.keywords, f, ensure_ascii=False, indent=2)
        st.success("Đã lưu từ khóa vào keywords.json")
    except Exception as e:
        st.error(f"Lưu keywords.json thất bại: {e}")

# Load dữ liệu ngay khi khởi chạy nếu chưa có
if not any(st.session_state.keywords.values()):
    st.session_state.keywords = load_keywords()

# ---------- Giao diện chính ----------
st.title("Chèn Link Tự Động - TGDĐ / ĐMX / TopZone")

# Khu vực 1: Quản lý từ khóa (Sidebar hoặc Top)
web_var = st.selectbox("Chọn Web:", WEB_OPTIONS)

st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Quản lý Từ khóa")
    
    # Form thêm từ khóa
    with st.form("add_keyword_form"):
        new_kw = st.text_input("Từ khóa mới:")
        new_url = st.text_input("Link:")
        submitted = st.form_submit_button("Thêm từ khóa")
        if submitted:
            if new_kw and new_url:
                st.session_state.keywords[web_var][new_kw.strip()] = new_url.strip()
                save_keywords()
                st.rerun()
            else:
                st.warning("Vui lòng nhập đầy đủ Từ khóa và Link.")

    # Nạp từ khóa từ File
    uploaded_file = st.file_uploader("Nạp file từ khóa (JSON hoặc CSV)", type=['json', 'csv'])
    if uploaded_file is not None:
        if st.button("Xử lý file nạp"):
            try:
                if uploaded_file.name.endswith('.json'):
                    data = json.load(uploaded_file)
                    st.session_state.keywords[web_var].update(data.get(web_var, data))
                elif uploaded_file.name.endswith('.csv'):
                    content = uploaded_file.getvalue().decode("utf-8").splitlines()
                    for line in content:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 2:
                            st.session_state.keywords[web_var][parts[0]] = parts[1]
                save_keywords()
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi đọc file: {e}")

    # Bảng quản lý từ khóa hiện tại
    st.write(f"**Danh sách từ khóa hiện tại cho {web_var} (Tick để chọn dùng)**")
    
    # Chuyển đổi dict sang dataframe để dùng st.data_editor (quản lý tick box dễ hơn)
    kw_dict = st.session_state.keywords[web_var]
    if kw_dict:
        df_kw = pd.DataFrame([
            {"Chọn": True, "Từ khóa": k, "Link": v}
            for k, v in kw_dict.items()
        ])
    else:
        df_kw = pd.DataFrame(columns=["Chọn", "Từ khóa", "Link"])

    edited_df = st.data_editor(
        df_kw,
        column_config={"Chọn": st.column_config.CheckboxColumn("Sử dụng", default=True)},
        hide_index=True,
        use_container_width=True
    )
    
    # Nút xóa từ khóa
    if not df_kw.empty:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Xóa các từ khóa ĐÃ TICK", type="primary"):
                for index, row in edited_df.iterrows():
                    if row["Chọn"]:
                        st.session_state.keywords[web_var].pop(row["Từ khóa"], None)
                save_keywords()
                st.rerun()
        with col_btn2:
            if st.button("Xóa TOÀN BỘ từ khóa web này"):
                st.session_state.keywords[web_var].clear()
                save_keywords()
                st.rerun()

with col2:
    st.subheader("2. Nội dung bài viết")
    
    raw_text = st.text_area("Dán bài viết tại đây:", height=200)
    
    if st.button("Nhận diện đoạn văn"):
        if raw_text.strip():
            blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text.strip()) if b.strip()]
            st.session_state.paragraphs = blocks
            st.session_state.is_h3 = [False] * len(blocks)
            st.success(f"Đã phát hiện {len(blocks)} đoạn.")
        else:
            st.warning("Vui lòng nhập nội dung bài viết.")

    if st.session_state.paragraphs:
        st.write("**Chọn các đoạn muốn set thẻ `<h3>` (mặc định là `<p>`)**")
        
        # Tạo công cụ chọn nhanh
        col_all1, col_all2 = st.columns(2)
        with col_all1:
            if st.button("Chọn tất cả là H3"):
                st.session_state.is_h3 = [True] * len(st.session_state.paragraphs)
                st.rerun()
        with col_all2:
            if st.button("Bỏ chọn H3 (tất cả là P)"):
                st.session_state.is_h3 = [False] * len(st.session_state.paragraphs)
                st.rerun()

        # Hiển thị checkbox cho từng đoạn
        for i, p in enumerate(st.session_state.paragraphs):
            short_text = p if len(p) < 100 else p[:100] + "..."
            st.session_state.is_h3[i] = st.checkbox(
                f"Đoạn {i+1}: {short_text}", 
                value=st.session_state.is_h3[i], 
                key=f"p_{i}"
            )

st.divider()

# ---------- Khu vực 3: Sinh HTML & Preview ----------
st.subheader("3. Tạo HTML & Tải xuống")

if st.button("Tạo HTML", type="primary", use_container_width=True):
    if not st.session_state.paragraphs:
        st.error("Chưa có đoạn văn nào. Hãy dán text và bấm 'Nhận diện đoạn văn' trước.")
    else:
        # Lấy từ khóa được tick
        selected_kw = {}
        if not df_kw.empty:
            for index, row in edited_df.iterrows():
                if row["Chọn"]:
                    selected_kw[row["Từ khóa"]] = row["Link"]

        # Cấu trúc khối dữ liệu
        blocks = []
        for i, p in enumerate(st.session_state.paragraphs):
            tag = 'h3' if st.session_state.is_h3[i] else 'p'
            blocks.append({'tag': tag, 'text': p})

        # --- Chèn từ khóa tự nhận diện thông minh ---
        anchors_map = {}
        anchor_counter = 0

        def new_anchor_token(anchor_html):
            nonlocal anchor_counter
            token = f"[[ANCHOR_{anchor_counter}]]"
            anchors_map[token] = anchor_html
            anchor_counter += 1
            return token

        # Sắp xếp keyword theo độ dài giảm dần
        kw_items = sorted(selected_kw.items(), key=lambda x: len(x[0]), reverse=True)

        for kw, link in kw_items:
            pattern = re.compile(rf'\b{re.escape(kw)}\b', flags=re.IGNORECASE)
            anchor_html = f'<a href="{html.escape(link)}" target="_blank" title="Tham khảo sản phẩm {html.escape(kw)} đang kinh doanh tại {web_var}">{html.escape(kw)}</a>'
            token = new_anchor_token(anchor_html)
            done = False
            for b in blocks:
                if done:
                    break
                new_text, n = pattern.subn(lambda m: token, b['text'], count=1)
                if n > 0:
                    b['text'] = new_text
                    done = True

        # --- Render HTML ---
        token_regex = re.compile(r'(\[\[ANCHOR_\d+\]\])')
        final_parts = []
        for b in blocks:
            parts = token_regex.split(b['text'])
            rendered = []
            for part in parts:
                if part in anchors_map:
                    rendered.append(anchors_map[part])
                else:
                    rendered.append(html.escape(part).replace("\n", "<br/>"))
            inner = ''.join(rendered)
            final_parts.append(f"<{b['tag']}>{inner}</{b['tag']}>")

        final_html = "\n\n".join(final_parts)
        st.session_state.final_html = final_html

# Hiển thị Preview và Nút tải xuống nếu đã tạo HTML
if "final_html" in st.session_state:
    st.write("**Mã HTML xem trước:**")
    st.code(st.session_state.final_html, language="html")
    
    # Khung Preview thực tế
    with st.expander("Xem trước giao diện thực tế (Preview Render)"):
        st.components.v1.html(st.session_state.final_html, height=300, scrolling=True)

    # Nút Download File HTML
    full_export_html = (
        "<!doctype html>\n<html lang='vi'>\n<head>\n"
        "<meta charset='utf-8'>\n<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
        "<title>Bài viết</title>\n</head>\n<body>\n"
        + st.session_state.final_html + "\n</body>\n</html>"
    )
    
    st.download_button(
        label="Tải xuống File HTML",
        data=full_export_html,
        file_name="bai_viet_da_chen_link.html",
        mime="text/html",
        type="primary"
    )