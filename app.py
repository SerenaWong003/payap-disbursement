import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
import altair as alt
import requests

# --- Library สำหรับ PDF ---
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

# ==========================================
# 1. ตั้งค่าระบบ (Configuration)
# ==========================================
st.set_page_config(page_title="ระบบบริหารจัดการงบประมาณ มพย.", layout="wide", page_icon="🛡️")

DB_FILE = "database_claims.csv"
TARGET_FILE = "budget_targets.csv"
TEMPLATE_PDF = "ใบเบิก.pdf"         
FONT_FILE = "THSarabunNew.ttf"       
FONT_URL = "https://github.com/gungunss/ThaiFonts/raw/master/THSarabunNew.ttf"

# --- 🎯 ฐานข้อมูลพิกัดข้อความ (PDF CONFIG) จัดบล็อกใหม่ ---
# X = แนวนอน, Y = แนวตั้ง (ระยะห่างบรรทัดละประมาณ 25-30 point)
PDF_CONFIG = {
    "faculty":    (180, 755),  # หน่วยงาน
    "doc_no":     (120, 730),  # ที่ มพย
    "date_day":   (380, 730),  # วันที่
    "date_month": (430, 730),  # เดือน
    "date_year":  (500, 730),  # พ.ศ.
    "subject":    (120, 705),  # เรื่อง
    "to_who":     (120, 680),  # เรียน
    "attach_1":   (150, 655),  # สิ่งที่ส่งมาด้วย
    "check_req":  (75, 620),   # [X] ขอเบิกเงิน
    "amount":     (220, 620),  # จำนวนเงินตัวเลข
    "amount_txt": (380, 620),  # จำนวนเงินตัวอักษร
    "pay_to":     (150, 580),  # สั่งจ่ายให้
    "req_d":      (380, 580),  # รับเงินวันที่
    "req_m":      (420, 580),  # รับเงินเดือน
    "req_y":      (490, 580),  # รับเงิน พ.ศ.
    "check_bank": (75, 520),   # [X] เข้าบัญชีธนาคาร
    "bank_detail":(250, 520),  # ชื่อและเลขบัญชี
    "project":    (230, 490),  # ใช้ในกิจกรรมดังนี้
    "faculty_budget": (260, 460), # งบประมาณของหน่วยงาน
    "check_budget": (75, 430), # [X] ประเภทงบ
    "budget_cat": (180, 430),  # หมวดงบประมาณ
    "leader":     (360, 310),  # ชื่อผู้เบิกเงิน
    "position":   (360, 285),  # ตำแหน่ง
}

# --- Master Data ---
BUDGET_MASTER = {
    "541010001": "หมวดส่งเสริมการวิจัย", "521130002": "ค่าถ่ายเอกสาร",
    "521130004": "วัสดุสิ้นเปลืองสำนักงาน", "531111005": "ค่ายานพาหนะ",
    "521140007": "สัมมนาภายใน", "531104002": "ค่าไปรษณียากร"
}

FACULTY_MASTER = [
    "คณะนิติศาสตร์", "คณะบริหารธุรกิจ", "วิทยาลัยสหวิทยาการ",
    "คณะพยาบาลศาสตร์แมคคอร์มิค", "คณะเภสัชศาสตร์", "วิทยาลัยนานาชาติ",
    "วิทยาลัยดุริยศิลป์", "วิทยาลัยพระคริสต์ธรรมแมคกิลวารี",
    "บัณฑิตวิทยาลัย", "สำนักการศึกษาทั่วไป", "สำนักวิจัย", "สำนักบริการวิชาการ"
]

# ==========================================
# 2. ฟังก์ชันระบบจัดการไฟล์
# ==========================================

def check_and_download_font():
    if not os.path.exists(FONT_FILE):
        try:
            response = requests.get(FONT_URL)
            if response.status_code == 200:
                with open(FONT_FILE, "wb") as f: 
                    f.write(response.content)
        except: 
            pass

def init_files():
    if not os.path.exists(DB_FILE):
        cols = ["NO", "เลขที่ออก", "วัน", "เดือน", "ปี", "ผู้ลงนาม", "ถึง", "เรื่อง", 
                "คณะ", "หัวหน้าโครงการวิจัย", "ผู้ประสาน", "เงินที่อนุมัติ", 
                "จำนวนเงิน", "ชื่อโครงการ", "รหัสหมวด", "บันทึกเมื่อ", 
                "สิ่งที่ส่งมาด้วย", "จำนวนเงิน_ตัวอักษร", "สั่งจ่ายให้", "ธนาคาร", "ตำแหน่ง"]
        pd.DataFrame(columns=cols).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    
    if not os.path.exists(TARGET_FILE):
        pd.DataFrame(columns=["year_type", "year", "amount"]).to_csv(TARGET_FILE, index=False, encoding='utf-8-sig')
        
    check_and_download_font()

def get_current_date():
    now = datetime.now()
    thai_year = now.year + 543
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    month_str = thai_months[now.month - 1]
    return now, thai_year, f"{now.day} {month_str} {thai_year}", month_str

def get_next_doc_no():
    try:
        if not os.path.exists(DB_FILE): 
            return "0203/001"
            
        df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
        if df.empty: 
            return "0203/001"
            
        df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
        _, current_year, _, _ = get_current_date()
        
        if current_year > df['ปี'].max(): 
            return "0203/001"
            
        last_doc = str(df['เลขที่ออก'].iloc[-1])
        if "/" in last_doc: 
            return f"0203/{int(last_doc.split('/')[-1]) + 1:03d}"
            
        return "0203/001"
    except: 
        return "0203/001"

def process_data(df):
    if df.empty: 
        return df
        
    required_cols = ['ปี', 'เดือน', 'จำนวนเงิน', 'ปีงบประมาณ', 'ปีการศึกษา', 'ปีปฏิทิน']
    for col in required_cols:
        if col not in df.columns: 
            if col == 'จำนวนเงิน':
                df[col] = pd.Series(dtype='float')
            else:
                df[col] = pd.Series(dtype='int')
                
    df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
    df['เดือน'] = pd.to_numeric(df['เดือน'], errors='coerce').fillna(0).astype(int)
    df['จำนวนเงิน'] = pd.to_numeric(df['จำนวนเงิน'], errors='coerce').fillna(0.0)
    
    df['ปีงบประมาณ'] = df.apply(lambda x: x['ปี'] + 1 if x['เดือน'] >= 8 else x['ปี'], axis=1)
    df['ปีการศึกษา'] = df.apply(lambda x: x['ปี'] if x['เดือน'] >= 6 else x['ปี'] - 1, axis=1)
    df['ปีปฏิทิน'] = df['ปี']
    
    return df

# ==========================================
# 3. PDF Generator & Budget Functions
# ==========================================
def get_target_budget(year_type, year):
    if not os.path.exists(TARGET_FILE): 
        return 0.0
    try:
        df = pd.read_csv(TARGET_FILE)
        match = df[(df['year_type'] == year_type) & (df['year'] == year)]
        if not match.empty: 
            return float(match['amount'].iloc[0])
        return 0.0
    except: 
        return 0.0

def save_target_budget(year_type, year, amount):
    if not os.path.exists(TARGET_FILE):
        df = pd.DataFrame(columns=["year_type", "year", "amount"])
    else: 
        df = pd.read_csv(TARGET_FILE)
        
    df = df[~((df['year_type'] == year_type) & (df['year'] == year))]
    new_row = pd.DataFrame([{"year_type": year_type, "year": year, "amount": amount}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(TARGET_FILE, index=False, encoding='utf-8-sig')

def create_filled_pdf(data):
    if not os.path.exists(TEMPLATE_PDF):
        st.error(f"❌ ไม่พบไฟล์ {TEMPLATE_PDF}")
        return None
    
    font_name = "Helvetica"
    if os.path.exists(FONT_FILE):
        pdfmetrics.registerFont(TTFont('ThaiFont', FONT_FILE))
        font_name = 'ThaiFont'
    
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(font_name, 14)

    def draw(key, text):
        base_x, base_y = PDF_CONFIG[key]
        can.drawString(base_x, base_y, str(text))

    # --- วาดข้อความลง PDF ---
    draw("faculty", data.get("คณะ", ""))
    draw("doc_no", data.get("เลขที่ออก", ""))
    draw("date_day", data["วัน"])
    draw("date_month", data["เดือน_ตัวอักษร"])
    draw("date_year", data["ปี"])
    
    draw("subject", data.get("เรื่อง", ""))
    draw("to_who", data.get("ถึง", ""))
    draw("attach_1", data.get("สิ่งที่ส่งมาด้วย", "-"))
    
    can.setFont("Helvetica-Bold", 14)
    draw("check_req", "X")
    can.setFont(font_name, 14)
    
    draw("amount", f"{data['จำนวนเงิน']:,.2f}")
    draw("amount_txt", f"({data.get('จำนวนเงิน_ตัวอักษร', '')})")
    
    draw("pay_to", data.get("สั่งจ่ายให้", ""))
    draw("req_d", data["วัน"])
    draw("req_m", data["เดือน_ตัวอักษร"])
    draw("req_y", data["ปี"])
    
    if data.get("ธนาคาร", "") != "":
        can.setFont("Helvetica-Bold", 14)
        draw("check_bank", "X")
        can.setFont(font_name, 12)
        draw("bank_detail", data.get("ธนาคาร", ""))
        can.setFont(font_name, 14)
    
    draw("project", data.get("ชื่อโครงการ", ""))
    draw("faculty_budget", data.get("คณะ", ""))
    
    can.setFont("Helvetica-Bold", 14)
    draw("check_budget", "X")
    can.setFont(font_name, 14)
    draw("budget_cat", data.get("รหัสหมวด", ""))
    
    draw("leader", f"({data.get('หัวหน้าโครงการวิจัย', '')})")
    draw("position", data.get("ตำแหน่ง", ""))

    can.save()
    packet.seek(0)
    
    try:
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
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

def plot_donut_chart(data, category_col, value_col):
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
# 4. Main UI
# ==========================================
init_files()

# --- Sidebar ---
st.sidebar.title("🛡️ เมนูหลัก")
menu = st.sidebar.radio("เลือกเมนู", ["📝 บันทึกตั้งเบิก", "📊 สรุปและคุมงบประมาณ"])

st.sidebar.markdown("---")
if st.sidebar.button("⚠️ ล้างฐานข้อมูลทั้งหมด"):
    if os.path.exists(DB_FILE): 
        os.remove(DB_FILE)
    if os.path.exists(TARGET_FILE): 
        os.remove(TARGET_FILE)
    if os.path.exists(FONT_FILE): 
        os.remove(FONT_FILE)
    init_files()
    st.sidebar.success("ล้างข้อมูลเรียบร้อย!")
    st.rerun()

# --- หน้าบันทึก ---
if menu == "📝 บันทึกตั้งเบิก":
    now, thai_year, date_str, month_str = get_current_date()
    st.title(f"📝 บันทึกขออนุมัติเบิกจ่าย")
    next_doc = get_next_doc_no()
    st.info(f"เลขที่เอกสารปัจจุบัน: **{next_doc}** | วันที่: {date_str}")

    if 'pdf_bytes' not in st.session_state: 
        st.session_state['pdf_bytes'] = None

    with st.form("entry_form", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
