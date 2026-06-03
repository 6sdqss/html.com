import streamlit as st
import json
import re
import os
import html

# ---------- Cấu hình ----------
KEYWORD_FILE = "keywords.json"
WEB_OPTIONS = ["Thế Giới Di Động", "Điện Máy Xanh", "TopZone"]

st.set_page_config(page_title="Thế Giới Di Động / Điện Máy Xanh / TopZone Link Tool", layout="wide")

# ---------- Khởi tạo Session State ----------
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

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

# Khởi tạo các biến hệ thống
init_state("keywords", load_keywords())
init_state("paragraphs", [])
init_state("final_html", "")
init_state("show_download", False)
init_state("web_var", WEB_OPTIONS[0])
init_state("raw_text_input", "")
init_state("entry_kw", "")
init_state("entry_url", "")

# Khởi tạo trạng thái checkbox cho các từ khóa đã lưu
for w in WEB_OPTIONS:
    for k in st.session_state.keywords[w]:
        init_state(f"kw_chk_{w}_{k}", False)

# ---------- Các hàm xử lý (Mô phỏng 1:1 Tkinter) ----------
def save_keywords():
    try:
        with open(KEYWORD_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.keywords, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Lưu keywords.json thất bại: {e}")

def add_keyword():
    kw = st.session_state.entry_kw.strip()
    url = st.session_state.entry_url.strip()
    w = st.session_state.web_var
    
    if not kw or not url:
        st.warning("Thiếu dữ liệu: Vui lòng nhập đầy đủ Từ khóa và Link.")
        return
    
    st.session_state.keywords[w][kw] = url
    st.session_state[f"kw_chk_{w}_{kw}"] = False  # Mặc định chưa được chọn
    save_keywords()
    st.success(f"Đã lưu từ khóa '{kw}' cho {w}")
    
    # Xóa trắng ô input sau khi thêm
    st.session_state.entry_kw = ""
    st.session_state.entry_url = ""

def select_all_keywords():
    w = st.session_state.web_var
    for k in st.session_state.keywords[w]:
        st.session_state[f"kw_chk_{w}_{k}"] = True

def deselect_all_keywords():
    w = st.session_state.web_var
    for k in st.session_state.keywords[w]:
        st.session_state[f"kw_chk_{w}_{k}"] = False

def clear_saved_keywords():
    w = st.session_state.web_var
    for k in list(st.session_state.keywords[w].keys()):
        st.session_state.pop(f"kw_chk_{w}_{k}", None)
    st.session_state.keywords[w].clear()
    save_keywords()
    st.success("Đã xóa toàn bộ từ khóa của web này.")

def delete_selected_keyword():
    w = st.session_state.web_var
    to_delete = []
    for k in st.session_state.keywords[w]:
        if st.session_state.get(f"kw_chk_{w}_{k}", False):
            to_delete.append(k)
            
    if not to_delete:
        st.warning("Chưa chọn: Vui lòng tick vào từ khóa muốn xóa.")
        return
        
    for k in to_delete:
        del st.session_state.keywords[w][k]
        st.session_state.pop(f"kw_chk_{w}_{k}", None)
    save_keywords()
    st.success(f"Đã xóa {len(to_delete)} từ khóa.")

def detect_paragraphs():
    raw = st.session_state.raw_text_input.strip()
    if not raw:
        st.warning("Thiếu nội dung: Vui lòng nhập nội dung bài viết vào TextBox bên dưới.")
        return
        
    blocks = [b.strip() for b in re.split(r'\n\s*\n', raw) if b.strip()]
    st.session_state.paragraphs = blocks
    for i in range(len(blocks)):
        st.session_state[f"par_chk_{i}"] = False
    st.success(f"Đã phát hiện {len(blocks)} đoạn được nhận diện.")

def select_all_pars():
    for i in range(len(st.session_state.paragraphs)):
        st.session_state[f"par_chk_{i}"] = True

def deselect_all_pars():
    for i in range(len(st.session_state.paragraphs)):
        st.session_state[f"par_chk_{i}"] = False

def generate_html(preview_only=True):
    raw = st.session_state.raw_text_input.strip()
    if not raw:
        st.warning("Thiếu nội dung: Vui lòng dán bài viết vào trước.")
        return

    w = st.session_state.web_var
    selected_kw = {}
    for k, link in st.session_state.keywords[w].items():
        if st.session_state.get(f"kw_chk_{w}_{k}", False):
            selected_kw[k] = link

    # Logic lấy định dạng h3 hay p
    if st.session_state.paragraphs:
        paragraphs = st.session_state.paragraphs
        is_h3 = [st.session_state.get(f"par_chk_{i}", False) for i in range(len(paragraphs))]
    else:
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]
        is_h3 = [False] * len(paragraphs)

    blocks = []
    for i, p in enumerate(paragraphs):
        tag = 'h3' if is_h3[i] else 'p'
        blocks.append({'tag': tag, 'text': p})

    # --- Chèn Anchor / Link ---
    anchors_map = {}
    anchor_counter = [0]
    
    def new_anchor_token(anchor_html):
        token = f"[[ANCHOR_{anchor_counter[0]}]]"
        anchors_map[token] = anchor_html
        anchor_counter[0] += 1
        return token

    kw_items = sorted(selected_kw.items(), key=lambda x: len(x[0]), reverse=True)

    for kw, link in kw_items:
        pattern = re.compile(rf'\b{re.escape(kw)}\b', flags=re.IGNORECASE)
        anchor_html = f'<a href="{html.escape(link)}" target="_blank" title="Tham khảo sản phẩm {html.escape(kw)} đang kinh doanh tại {w}">{html.escape(kw)}</a>'
        token = new_anchor_token(anchor_html)
        done = False
        for b in blocks:
            if done:
                break
            new_text, n = pattern.subn(lambda m: token, b['text'], count=1)
            if n > 0:
                b['text'] = new_text
                done = True

    # --- Render ra HTML cuối cùng ---
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
    st.session_state.show_download = not preview_only


# ==========================================
#                  GIAO DIỆN
# ==========================================
col_left, col_right = st.columns([1.2, 1])

# ------------- KHUNG BÊN TRÁI -------------
with col_left:
    # 1. Các nút hành động chính và Cấu hình Web
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        st.button("Tạo & Xem trước", on_click=generate_html, args=(True,), use_container_width=True)
    with c_btn2:
        st.button("Hoàn thành (Xuất HTML)", on_click=generate_html, args=(False,), type="primary", use_container_width=True)
        
    st.selectbox("Chọn Web:", WEB_OPTIONS, key="web_var")
    
    st.divider()
    
    # 2. Khu vực Quản lý Từ khóa
    st.write("**Từ khóa và link:**")
    kw_c1, kw_c2, kw_c3 = st.columns([2, 3, 1])
    with kw_c1:
        st.text_input("Từ khóa:", key="entry_kw")
    with kw_c2:
        st.text_input("Link:", key="entry_url")
    with kw_c3:
        st.write("") 
        st.write("") 
        st.button("Thêm", on_click=add_keyword, use_container_width=True)
        
    with st.expander("Nạp file từ khóa (JSON hoặc CSV)"):
        uploaded_file = st.file_uploader("Chọn file:", type=['json', 'csv'], label_visibility="collapsed")
        if uploaded_file and st.button("Xử lý nạp file"):
            try:
                w = st.session_state.web_var
                if uploaded_file.name.endswith(".json"):
                    data = json.load(uploaded_file)
                    st.session_state.keywords[w].update(data.get(w, data))
                else:
                    content = uploaded_file.getvalue().decode("utf-8").splitlines()
                    for line in content:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 2:
                            st.session_state.keywords[w][parts[0]] = parts[1]
                
                # Cập nhật state check cho các từ vừa nạp
                for k in st.session_state.keywords[w]:
                    init_state(f"kw_chk_{w}_{k}", False)
                save_keywords()
                st.success("Đã nạp danh sách từ khóa.")
            except Exception as e:
                st.error(f"Lỗi đọc file: {e}")

    # Nút điều khiển Keyword
    kw_ctrl1, kw_ctrl2, kw_ctrl3, kw_ctrl4 = st.columns(4)
    with kw_ctrl1: st.button("Chọn tất cả", on_click=select_all_keywords, use_container_width=True)
    with kw_ctrl2: st.button("Bỏ chọn tất cả", on_click=deselect_all_keywords, use_container_width=True)
    with kw_ctrl3: st.button("Xóa tất cả", on_click=clear_saved_keywords, use_container_width=True)
    with kw_ctrl4: st.button("Xóa từ chọn", on_click=delete_selected_keyword, use_container_width=True)

    # Frame Scrollable cho Keyword (Khung cuộn ngang/dọc)
    st.write("Chọn từ khóa muốn chèn (tick những từ dùng):")
    kw_box = st.container(height=180)
    with kw_box:
        w = st.session_state.web_var
        for k, v in st.session_state.keywords[w].items():
            st.checkbox(f"{k} → {v}", key=f"kw_chk_{w}_{k}")

    st.divider()

    # 3. Khu vực Dán Bài Viết và Chọn Đoạn H3
    st.write("**Dán bài viết tại đây:**")
    st.text_area("", height=220, key="raw_text_input", label_visibility="collapsed")

    # Nút điều khiển Paragraph
    p_ctrl1, p_ctrl2, p_ctrl3 = st.columns(3)
    with p_ctrl1: st.button("Detect đoạn", on_click=detect_paragraphs, use_container_width=True)
    with p_ctrl2: st.button("Chọn tất cả (Set H3)", on_click=select_all_pars, use_container_width=True)
    with p_ctrl3: st.button("Bỏ chọn (Set p)", on_click=deselect_all_pars, use_container_width=True)

    # Frame Scrollable cho Các Đoạn (Tick để set thẻ H3)
    par_box = st.container(height=180)
    with par_box:
        for i, p in enumerate(st.session_state.paragraphs):
            short = p if len(p) < 140 else p[:140] + "..."
            st.checkbox(f"Đoạn {i+1}: {short}", key=f"par_chk_{i}")

# ------------- KHUNG BÊN PHẢI -------------
with col_right:
    st.write("**Preview HTML:**")
    st.text_area("", value=st.session_state.final_html, height=750, disabled=True, label_visibility="collapsed")
    st.caption("* Kiểm tra kỹ trước khi dán vào CMS")
    
    # Nút Export (Chỉ hiện khi nhấn nút "Hoàn thành")
    if st.session_state.show_download and st.session_state.final_html:
        full_export_html = (
            "<!doctype html>\n<html lang='vi'>\n<head>\n"
            "<meta charset='utf-8'>\n<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
            "<title>Bài viết</title>\n</head>\n<body>\n"
            + st.session_state.final_html + "\n</body>\n</html>"
        )
        st.download_button(
            label="📥 Tải xuống File HTML",
            data=full_export_html,
            file_name="bai_viet.html",
            mime="text/html",
            type="primary",
            use_container_width=True
        )
