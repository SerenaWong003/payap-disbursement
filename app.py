import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
import altair as alt

# --- Library สำหรับจัดการ PDF ---
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

# ==========================================
# 1. ตั้งค่าระบบ (Configuration)
# ==========================================
st.set_page_config(page_title="ระบบบริหารจัดการงบประมาณ มพย.", layout="wide", page_icon="🛡️")

# ชื่อไฟล์ฐานข้อมูลและไฟล์ประกอบ
DB_FILE = "database_claims.csv"      # เก็บข้อมูลการเบิกจ่าย
TARGET_FILE = "budget_targets.csv"   # เก็บงบประมาณตั้งต้น
TEMPLATE_PDF = "ใบเบิก.pdf"          # ไฟล์แบบฟอร์มเปล่า (ต้องอัปโหลดขึ้น GitHub)
FONT_FILE = "THSarabunNew.ttf"       # ไฟล์ฟอนต์ไทย (ต้องอัปโหลดขึ้น GitHub)

# --- พิกัดข้อความสำหรับใบเบิก PDF (ปรับแก้ตำแหน่ง X, Y ได้ที่นี่) ---
# หน่วยเป็น Point (X แนวนอน, Y แนวตั้ง วัดจากมุมล่างซ้าย)
PDF_CONFIG = {
    "date_day":   (370, 715),  # วันที่
    "date_month": (420, 715),  # เดือน
    "date_year":  (480, 715),  # พ.ศ.
    "subject":    (100, 680),  # เรื่อง
    "amount":     (150, 560),  # จำนวนเงิน (ตัวเลข)
    "budget_cat": (200, 460),  # ประเภทงบประมาณ
    "leader":     (350, 200),  # ชื่อผู้เบิก (ตำแหน่งเซ็นชื่อ)
}

# --- ข้อมูลหลัก (Master Data) ---
BUDGET_MASTER = {
    "541010001": "หมวดส่งเสริมการวิจัย",
    "521130002": "ค่าถ่ายเอกสาร",
    "521130004": "วัสดุสิ้นเปลืองสำนักงาน",
    "531111005": "ค่ายานพาหนะ",
    "521140007": "สัมมนาภายใน",
    "531104002": "ค่าไปรษณียากร"
}

FACULTY_MASTER = [
    "คณะนิติศาสตร์", "คณะบริหารธุรกิจ", "วิทยาลัยสหวิทยาการ",
    "คณะพยาบาลศาสตร์แมคคอร์มิค", "คณะเภสัชศาสตร์", "วิทยาลัยนานาชาติ",
    "วิทยาลัยดุริยศิลป์", "วิทยาลัยพระคริสต์ธรรมแมคกิลวารี",
    "บัณฑิตวิทยาลัย", "สำนักการศึกษาทั่วไป"
]

# ==========================================
# 2. ฟังก์ชันระบบจัดการไฟล์และข้อมูล
# ==========================================

def init_files():
    """สร้างไฟล์ CSV เริ่มต้นถ้ายังไม่มี"""
    if not os.path.exists(DB_FILE):
        cols = ["NO", "เลขที่ออก", "วัน", "เดือน", "ปี", "ผู้ลงนาม", "ถึง", "เรื่อง", 
                "คณะ", "หัวหน้าโครงการวิจัย", "ผู้ประสาน", "เงินที่อนุมัติ", 
                "จำนวนเงิน", "ชื่อโครงการ", "รหัสหมวด", "บันทึกเมื่อ"]
        pd.DataFrame(columns=cols).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    
    if not os.path.exists(TARGET_FILE):
        pd.DataFrame(columns=["year_type", "year", "amount"]).to_csv(TARGET_FILE, index=False, encoding='utf-8-sig')

def get_current_date():
    """ดึงวันที่ปัจจุบันและชื่อเดือนภาษาไทย"""
    now = datetime.now()
    thai_year = now.year + 543
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    month_str = thai_months[now.month - 1]
    return now, thai_year, f"{now.day} {month_str} {thai_year}", month_str

def get_next_doc_no():
    """รันเลขที่เอกสารอัตโนมัติ (รีเซ็ตทุกปี)"""
    try:
        if not os.path.exists(DB_FILE): return "0203/001"
        df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
        if df.empty: return "0203/001"
        
        # แปลงปีเป็นตัวเลขเพื่อเปรียบเทียบ
        df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
        _, current_year, _, _ = get_current_date()
        
        # ถ้าขึ้นปีใหม่ รีเซ็ตเลขเป็น 001
        if current_year > df['ปี'].max():
            return "0203/001"
            
        last_doc = str(df['เลขที่ออก'].iloc[-1])
        if "/" in last_doc:
            return f"0203/{int(last_doc.split('/')[-1]) + 1:03d}"
        return "0203/001"
    except:
        return "0203/001"

def process_data(df):
    """ประมวลผลข้อมูล: คำนวณปีงบประมาณและปีการศึกษา"""
    # สร้างคอลัมน์รอไว้เสมอเพื่อกัน Error (KeyError Fix)
    required_cols = ['ปี', 'เดือน', 'จำนวนเงิน', 'ปีงบประมาณ', 'ปีการศึกษา', 'ปีปฏิทิน']
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype='float' if col == 'จำนวนเงิน' else 'int')

    if df.empty: return df

    # แปลงข้อมูลเป็นตัวเลขจริง
    df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
    df['เดือน'] = pd.to_numeric(df['เดือน'], errors='coerce').fillna(0).astype(int)
    df['จำนวนเงิน'] = pd.to_numeric(df['จำนวนเงิน'], errors='coerce').fillna(0.0)

    # สูตรคำนวณปี
    # ปีงบประมาณ (เริ่ม ส.ค.)
    df['ปีงบประมาณ'] = df.apply(lambda x: x['ปี'] + 1 if x['เดือน'] >= 8 else x['ปี'], axis=1)
    # ปีการศึกษา (เริ่ม มิ.ย.)
    df['ปีการศึกษา'] = df.apply(lambda x: x['ปี'] if x['เดือน'] >= 6 else x['ปี'] - 1, axis=1)
    # ปีปฏิทิน
    df['ปีปฏิทิน'] = df['ปี']
    
    return df

# ==========================================
# 3. ฟังก์ชันจัดการงบประมาณ (Budget)
# ==========================================

def get_target_budget(year_type, year):
    """ดึงข้อมูลงบประมาณตั้งต้น"""
    if not os.path.exists(TARGET_FILE): return 0.0
    try:
        df = pd.read_csv(TARGET_FILE)
        match = df[(df['year_type'] == year_type) & (df['year'] == year)]
        if not match.empty: return float(match['amount'].iloc[0])
        return 0.0
    except: return 0.0

def save_target_budget(year_type, year, amount):
    """บันทึกงบประมาณตั้งต้น"""
    if not os.path.exists(TARGET_FILE):
        df = pd.DataFrame(columns=["year_type", "year", "amount"])
    else:
        df = pd.read_csv(TARGET_FILE)
    
    # ลบข้อมูลเก่าแล้วบันทึกทับ (Upsert)
    df = df[~((df['year_type'] == year_type) & (df['year'] == year))]
    new_row = pd.DataFrame([{"year_type": year_type, "year": year, "amount": amount}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(TARGET_FILE, index=False, encoding='utf-8-sig')

# ==========================================
# 4. ฟังก์ชันสร้าง PDF และกราฟ
# ==========================================

def create_filled_pdf(data):
    """สร้างไฟล์ PDF โดยเขียนทับแบบฟอร์มเดิม"""
    if not os.path.exists(TEMPLATE_PDF):
        st.error(f"❌ ไม่พบไฟล์ {TEMPLATE_PDF} กรุณาอัปโหลดขึ้น GitHub")
        return None
    
    # ตรวจสอบฟอนต์
    font_name = "Helvetica" # Default
    if os.path.exists(FONT_FILE):
        pdfmetrics.registerFont(TTFont('ThaiFont', FONT_FILE))
        font_name = 'ThaiFont'
    else:
        st.warning("⚠️ ไม่พบฟอนต์ไทย ระบบจะใช้ฟอนต์มาตรฐาน (ภาษาไทยอาจไม่แสดงผล)")

    # เริ่มเขียน PDF ลงในหน่วยความจำ (RAM)
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(font_name, 14)

    # วาดข้อมูลตามพิกัด (ดึงจาก PDF_CONFIG)
    can.drawString(PDF_CONFIG["date_day"][0], PDF_CONFIG["date_day"][1], str(data["วัน"]))
    can.drawString(PDF_CONFIG["date_month"][0], PDF_CONFIG["date_month"][1], str(data["เดือน_ตัวอักษร"]))
    can.drawString(PDF_CONFIG["date_year"][0], PDF_CONFIG["date_year"][1], str(data["ปี"]))
    
    can.drawString(PDF_CONFIG["subject"][0], PDF_CONFIG["subject"][1], data["เรื่อง"])
    can.drawString(PDF_CONFIG["amount"][0], PDF_CONFIG["amount"][1], f"{data['จำนวนเงิน']:,.2f}")
    
    # ลดขนาดฟอนต์สำหรับหมวดงบ
    can.setFont(font_name, 12)
    can.drawString(PDF_CONFIG["budget_cat"][0], PDF_CONFIG["budget_cat"][1], data["รหัสหมวด"])
    
    # ชื่อผู้เบิก
    can.setFont(font_name, 14)
    can.drawString(PDF_CONFIG["leader"][0], PDF_CONFIG["leader"][1], f"({data['หัวหน้าโครงการวิจัย']})")

    can.save()
    packet.seek(0)
    
    # รวมร่างกับไฟล์ต้นฉบับ
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(open(TEMPLATE_PDF, "rb"))
    output = PdfWriter()
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    
    out_stream = io.BytesIO()
    output.write(out_stream)
    out_stream.seek(0)
    return out_stream

def plot_donut_chart(data, category_col, value_col, title):
    """สร้างกราฟ Donut Chart ด้วย Altair (ทนทาน ไม่พังง่าย)"""
    if data.empty:
        st.info("ไม่มีข้อมูล")
        return

    base = alt.Chart(data).encode(theta=alt.Theta(value_col, stack=True))
    pie = base.mark_arc(innerRadius=60).encode(
        color=alt.Color(category_col),
        order=alt.Order(value_col, sort="descending"),
        tooltip=[category_col, alt.Tooltip(value_col, format=",.2f")]
    )
    text = base.mark_text(radius=140).encode(
        text=alt.Text(value_col, format=",.0f"),
        order=alt.Order(value_col, sort="descending"),
        color=alt.value("black")  
    )
    st.altair_chart(pie + text, use_container_width=True)

# ==========================================
# 5. ส่วนแสดงผลหลัก (Main UI)
# ==========================================

init_files() # เริ่มต้นระบบ

# เมนู Sidebar
st.sidebar.title("🛡️ เมนูหลัก")
menu = st.sidebar.radio("เลือกเมนู", ["📝 บันทึกตั้งเบิก", "📊 สรุปและคุมงบประมาณ"])

st.sidebar.markdown("---")
# ปุ่มล้างข้อมูล (ใช้เมื่อระบบมีปัญหา)
if st.sidebar.button("⚠️ ล้างฐานข้อมูลทั้งหมด"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(TARGET_FILE): os.remove(TARGET_FILE)
    init_files()
    st.sidebar.success("ล้างข้อมูลเรียบร้อย! โปรดรีเฟรชหน้าเว็บ")

# ------------------------------------------
# หน้าที่ 1: บันทึกตั้งเบิก (Entry & Print)
# ------------------------------------------
if menu == "📝 บันทึกตั้งเบิก":
    now, thai_year, date_str, month_str = get_current_date()
    st.title(f"📝 บันทึกขออนุมัติเบิกจ่าย")
    
    next_doc = get_next_doc_no()
    st.info(f"เลขที่เอกสารปัจจุบัน: **{next_doc}** | วันที่: {date_str}")

    # ใช้ Session State เก็บไฟล์ PDF เพื่อไม่ให้หายเวลากดปุ่ม
    if 'pdf_bytes' not in st.session_state:
        st.session_state['pdf_bytes'] = None

    with st.form("entry_form", clear_on_submit=False):
        col_topic, col_to = st.columns([2, 1])
        with col_topic: subject = st.text_input("เรื่อง")
        with col_to: to_who = st.text_input("เรียน", value="รองอธิการบดีฝ่ายวิชาการและวิจัย")
            
        c1, c2 = st.columns(2)
        with c1:
            project = st.text_input("ชื่อโครงการวิจัย")
            budget_total = st.number_input("งบประมาณโครงการ (บาท)", min_value=0.0, format="%.2f")
            faculty = st.selectbox("คณะ / หน่วยงาน", FACULTY_MASTER)
        with c2:
            leader = st.text_input("ชื่อหัวหน้าโครงการ")
            amount = st.number_input("ยอดเบิกครั้งนี้ (บาท)", min_value=0.0, format="%.2f")
            budget_cat = st.selectbox("หมวดงบประมาณ", list(BUDGET_MASTER.keys()), format_func=lambda x: f"{x} - {BUDGET_MASTER[x]}")

        # ปุ่ม Submit
        submitted = st.form_submit_button("✅ บันทึกข้อมูลและสร้างใบเบิก")

    if submitted:
        if not subject or not project:
            st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
        else:
            # 1. บันทึก CSV
            new_data = {
                "NO": "", "เลขที่ออก": next_doc,
                "วัน": now.day, "เดือน": now.month, "ปี": thai_year,
                "ผู้ลงนาม": "ผู้อำนวยการ", "ถึง": to_who, "เรื่อง": subject,
                "คณะ": faculty, "หัวหน้าโครงการวิจัย": leader,
                "ผู้ประสาน": "", "เงินที่อนุมัติ": budget_total,
                "จำนวนเงิน": amount, "ชื่อโครงการ": project,
                "รหัสหมวด": f"{budget_cat} {BUDGET_MASTER[budget_cat]}",
                "บันทึกเมื่อ": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            pd.DataFrame([new_data]).to_csv(DB_FILE, mode='a', index=False, header=False, encoding='utf-8-sig')
            st.success(f"บันทึกสำเร็จ! เลขที่ {next_doc}")
            
            # 2. สร้าง PDF
            pdf_data = new_data.copy()
            pdf_data['เดือน_ตัวอักษร'] = month_str
            st.session_state['pdf_bytes'] = create_filled_pdf(pdf_data)

    # แสดงปุ่มดาวน์โหลด PDF (ถ้ามีข้อมูล)
    if st.session_state['pdf_bytes']:
        st.markdown("---")
        st.subheader("🖨️ พิมพ์เอกสาร")
        col_d1, col_d2 = st.columns([1, 4])
        with col_d1:
            st.download_button(
                label="📄 ดาวน์โหลดใบเบิก (PDF)",
                data=st.session_state['pdf_bytes'],
                file_name=f"ใบเบิก_{next_doc.replace('/', '-')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        with col_d2:
            st.info("👆 กดปุ่มเพื่อดาวน์โหลดใบเบิกที่กรอกข้อมูลแล้ว")

# ------------------------------------------
# หน้าที่ 2: สรุปและคุมงบประมาณ (Dashboard)
# ------------------------------------------
elif menu == "📊 สรุปและคุมงบประมาณ":
    st.title("📊 ศูนย์บัญชาการงบประมาณ")
    
    try: raw_df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
    except: raw_df = pd.DataFrame()
        
    df = process_data(raw_df)

    # --- ส่วนกรองข้อมูล (Filter) ---
    with st.container():
        st.markdown("##### 🔍 ตัวกรองข้อมูล")
        c1, c2 = st.columns(2)
        with c1:
            year_type_options = ["ปีงบประมาณ", "ปีพุทธศักราช", "ปีการศึกษา"]
            selected_type_label = st.selectbox("1. เลือกประเภทปี", year_type_options)
            
            type_map = {"ปีงบประมาณ": "ปีงบประมาณ", "ปีพุทธศักราช": "ปีปฏิทิน", "ปีการศึกษา": "ปีการศึกษา"}
            selected_col = type_map[selected_type_label]

        with c2:
            current_y = datetime.now().year + 543
            # หาปีที่มีข้อมูลมาแสดง
            if not df.empty and df['ปี'].sum() > 0:
                available_years = sorted(df[selected_col].unique(), reverse=True)
                if current_y not in available_years: available_years.insert(0, current_y)
            else:
                available_years = [current_y]
                
            selected_year = st.selectbox("2. เลือกปี (พ.ศ.)", available_years)

    st.markdown("---")

    # --- ส่วนตั้งงบประมาณ (Budget Setting) ---
    with st.expander("⚙️ ตั้งค่าวงเงินงบประมาณ (Budget Setting)", expanded=True):
        col_set1, col_set2 = st.columns([3, 1])
        current_target = get_target_budget(selected_type_label, selected_year)
        
        with col_set1:
            target_input = st.number_input(
                f"งบประมาณรวมที่ได้รับจัดสรร ({selected_type_label} {selected_year})",
                min_value=0.0, value=current_target, format="%.2f"
            )
        with col_set2:
            st.write("")
            st.write("")
            if st.button("💾 บันทึกยอด"):
                save_target_budget(selected_type_label, selected_year, target_input)
                st.success("บันทึกวงเงินเรียบร้อย")
                st.rerun()

    # --- คำนวณยอดเงิน ---
    if not df.empty:
        filtered_df = df[df[selected_col] == selected_year]
    else:
        filtered_df = pd.DataFrame(columns=df.columns)

    total_spent = filtered_df['จำนวนเงิน'].sum()
    remaining_budget = target_input - total_spent
    percent_used = (total_spent / target_input * 100) if target_input > 0 else 0

    # --- แสดง Metrics ---
    st.markdown("### 📈 สถานะการเบิกจ่าย")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 งบที่ได้รับ", f"{target_input:,.2f} บาท")
    m2.metric("💸 ใช้ไปแล้ว", f"{total_spent:,.2f} บาท")
    m3.metric("เหลือใช้อีก", f"{remaining_budget:,.2f} บาท", delta=f"{percent_used:.1f}% used", delta_color="normal" if remaining_budget >=0 else "inverse")
    
    st.progress(min(percent_used / 100, 1.0))

    # --- แสดงกราฟ (Donut Chart) ---
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📊 สัดส่วนตามหมวดงบประมาณ")
        if not filtered_df.empty:
            cat_sum = filtered_df.groupby("รหัสหมวด")['จำนวนเงิน'].sum().reset_index()
            plot_donut_chart(cat_sum, "รหัสหมวด", "จำนวนเงิน", "สัดส่วนงบ")
            with st.expander("ดูตารางข้อมูล"):
                st.dataframe(cat_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else:
            st.info("ไม่มีข้อมูล")

    with col_chart2:
        st.subheader("🏢 สัดส่วนตามคณะ/หน่วยงาน")
        if not filtered_df.empty:
            fac_sum = filtered_df.groupby("คณะ")['จำนวนเงิน'].sum().reset_index()
            plot_donut_chart(fac_sum, "คณะ", "จำนวนเงิน", "สัดส่วนคณะ")
            with st.expander("ดูตารางข้อมูล"):
                st.dataframe(fac_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else:
            st.info("ไม่มีข้อมูล")

    # --- ปุ่มดาวน์โหลด CSV ---
    if not filtered_df.empty:
        st.markdown("---")
        with open(DB_FILE, "rb") as f:
            st.download_button("📥 ดาวน์โหลดข้อมูลทั้งหมด (CSV)", f, "database_claims.csv", "text/csv")
