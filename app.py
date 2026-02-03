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

# ไฟล์ระบบ
DB_FILE = "database_claims.csv"
TARGET_FILE = "budget_targets.csv"
TEMPLATE_PDF = "ใบเบิก.pdf"         
FONT_FILE = "THSarabunNew.ttf"       
FONT_URL = "https://github.com/gungunss/ThaiFonts/raw/master/THSarabunNew.ttf"

# --- 🎯 ตั้งค่าพิกัดข้อความ (PDF CONFIG) ---
# หน่วยเป็น Point (A4 กว้าง=595, สูง=842)
# X = แนวนอน (ซ้ายไปขวา), Y = แนวตั้ง (ล่างขึ้นบน)
PDF_CONFIG = {
    # บรรทัด 1: หน่วยงาน
    "faculty":    (130, 755),  
    
    # บรรทัด 2: เลขที่ + วันที่
    "doc_no":     (100, 730),  
    "date_day":   (380, 730),  
    "date_month": (440, 730),  
    "date_year":  (510, 730),  
    
    # บรรทัด 3: เรื่อง
    "subject":    (100, 705),  
    
    # บรรทัด 4: เรียน
    "to_who":     (100, 680),  
    
    # บรรทัด 5-6: สิ่งที่ส่งมาด้วย
    "attach_1":   (160, 655),  
    
    # บรรทัด 7: จำนวนเงิน (ตัวเลข และ ตัวอักษร)
    "amount":     (180, 605),  
    "amount_txt": (350, 605),  # อยู่บรรทัดเดียวกันเยื้องขวา
    
    # บรรทัด 8: สั่งจ่าย + วันรับเงิน
    "pay_to":     (120, 555),  
    "receive_date":(400, 555), 
    
    # บรรทัด 9: ธนาคาร (ขยับลงมาอีกนิด)
    "bank_detail":(250, 505),  
    
    # บรรทัด 10: โครงการ
    "project":    (200, 480),  
    
    # บรรทัด 11: หน่วยงาน
    "faculty_budget": (240, 455), 
    
    # บรรทัด 12: ประเภทงบ (ขยับลงมา)
    "budget_cat": (240, 430),  
    
    # ส่วนลงชื่อ (ย้ายลงมาด้านล่างขวา)
    "leader":     (370, 320),  
    "position":   (370, 300),  
}

# --- Master Data ---
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
    "บัณฑิตวิทยาลัย", "สำนักการศึกษาทั่วไป", "สำนักวิจัย"
]

# ==========================================
# 2. ฟังก์ชันระบบจัดการไฟล์
# ==========================================

def check_and_download_font():
    if not os.path.exists(FONT_FILE):
        try:
            response = requests.get(FONT_URL)
            if response.status_code == 200:
                with open(FONT_FILE, "wb") as f: f.write(response.content)
        except: pass

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
    thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                   "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    month_str = thai_months[now.month - 1]
    return now, thai_year, f"{now.day} {month_str} {thai_year}", month_str

def get_next_doc_no():
    try:
        if not os.path.exists(DB_FILE): return "0203/001"
        df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
        if df.empty: return "0203/001"
        df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
        _, current_year, _, _ = get_current_date()
        if current_year > df['ปี'].max(): return "0203/001"
        last_doc = str(df['เลขที่ออก'].iloc[-1])
        if "/" in last_doc: return f"0203/{int(last_doc.split('/')[-1]) + 1:03d}"
        return "0203/001"
    except: return "0203/001"

def process_data(df):
    if df.empty: return df
    required_cols = ['ปี', 'เดือน', 'จำนวนเงิน', 'ปีงบประมาณ', 'ปีการศึกษา', 'ปีปฏิทิน']
    for col in required_cols:
        if col not in df.columns: df[col] = pd.Series(dtype='float' if col == 'จำนวนเงิน' else 'int')
    
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
    if not os.path.exists(TARGET_FILE): return 0.0
    try:
        df = pd.read_csv(TARGET_FILE)
        match = df[(df['year_type'] == year_type) & (df['year'] == year)]
        if not match.empty: return float(match['amount'].iloc[0])
        return 0.0
    except: return 0.0

def save_target_budget(year_type, year, amount):
    if not os.path.exists(TARGET_FILE):
        df = pd.DataFrame(columns=["year_type", "year", "amount"])
    else: df = pd.read_csv(TARGET_FILE)
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

    # วาดข้อมูลตามพิกัดที่ตั้งไว้ด้านบน
    # 1. ส่วนหัว
    can.drawString(PDF_CONFIG["faculty"][0], PDF_CONFIG["faculty"][1], str(data.get("คณะ", "")))
    can.drawString(PDF_CONFIG["doc_no"][0], PDF_CONFIG["doc_no"][1], str(data.get("เลขที่ออก", "")))
    can.drawString(PDF_CONFIG["date_day"][0], PDF_CONFIG["date_day"][1], str(data["วัน"]))
    can.drawString(PDF_CONFIG["date_month"][0], PDF_CONFIG["date_month"][1], str(data["เดือน_ตัวอักษร"]))
    can.drawString(PDF_CONFIG["date_year"][0], PDF_CONFIG["date_year"][1], str(data["ปี"]))
    
    # 2. รายละเอียด
    can.drawString(PDF_CONFIG["subject"][0], PDF_CONFIG["subject"][1], str(data.get("เรื่อง", "")))
    can.drawString(PDF_CONFIG["to_who"][0], PDF_CONFIG["to_who"][1], str(data.get("ถึง", "")))
    can.drawString(PDF_CONFIG["attach_1"][0], PDF_CONFIG["attach_1"][1], str(data.get("สิ่งที่ส่งมาด้วย", "-")))
    
    # 3. การเงิน
    can.drawString(PDF_CONFIG["amount"][0], PDF_CONFIG["amount"][1], f"{data['จำนวนเงิน']:,.2f}")
    can.drawString(PDF_CONFIG["amount_txt"][0], PDF_CONFIG["amount_txt"][1], f"({data.get('จำนวนเงิน_ตัวอักษร', '')})")
    
    can.drawString(PDF_CONFIG["pay_to"][0], PDF_CONFIG["pay_to"][1], str(data.get("สั่งจ่ายให้", "")))
    can.drawString(PDF_CONFIG["receive_date"][0], PDF_CONFIG["receive_date"][1], f"{data['วัน']} {data['เดือน_ตัวอักษร']} {data['ปี']}")
    
    can.setFont(font_name, 12) # ลดขนาดนิดนึงสำหรับเลขบัญชี
    can.drawString(PDF_CONFIG["bank_detail"][0], PDF_CONFIG["bank_detail"][1], str(data.get("ธนาคาร", "")))
    can.setFont(font_name, 14)
    
    can.drawString(PDF_CONFIG["project"][0], PDF_CONFIG["project"][1], str(data.get("ชื่อโครงการ", "")))
    
    # 4. งบประมาณ
    can.drawString(PDF_CONFIG["faculty_budget"][0], PDF_CONFIG["faculty_budget"][1], str(data.get("คณะ", "")))
    can.drawString(PDF_CONFIG["budget_cat"][0], PDF_CONFIG["budget_cat"][1], str(data.get("รหัสหมวด", "")))
    
    # 5. ลงชื่อ
    can.drawString(PDF_CONFIG["leader"][0], PDF_CONFIG["leader"][1], f"({data.get('หัวหน้าโครงการวิจัย', '')})")
    can.drawString(PDF_CONFIG["position"][0], PDF_CONFIG["position"][1], str(data.get("ตำแหน่ง", "")))

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

def plot_donut_chart(data, category_col, value_col, title):
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

st.sidebar.title("🛡️ เมนูหลัก")
menu = st.sidebar.radio("เลือกเมนู", ["📝 บันทึกตั้งเบิก", "📊 สรุปและคุมงบประมาณ"])
st.sidebar.markdown("---")
if st.sidebar.button("⚠️ ล้างฐานข้อมูลทั้งหมด"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(TARGET_FILE): os.remove(TARGET_FILE)
    if os.path.exists(FONT_FILE): os.remove(FONT_FILE)
    init_files()
    st.sidebar.success("ล้างข้อมูลเรียบร้อย!")
    st.rerun()

# --- หน้าบันทึก ---
if menu == "📝 บันทึกตั้งเบิก":
    now, thai_year, date_str, month_str = get_current_date()
    st.title(f"📝 บันทึกขออนุมัติเบิกจ่าย")
    next_doc = get_next_doc_no()
    st.info(f"เลขที่เอกสารปัจจุบัน: **{next_doc}** | วันที่: {date_str}")

    if 'pdf_bytes' not in st.session_state: st.session_state['pdf_bytes'] = None

    with st.form("entry_form", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
        with c1: subject = st.text_input("เรื่อง")
        with c2: to_who = st.text_input("เรียน", value="หัวหน้าแผนกการเงิน")
        
        attachments = st.text_input("สิ่งที่ส่งมาด้วย")

        c3, c4 = st.columns(2)
        with c3: project = st.text_input("ใช้ในกิจกรรม (โครงการ)")
        with c4: faculty = st.selectbox("หน่วยงาน", FACULTY_MASTER)

        st.markdown("---")
        c5, c6 = st.columns(2)
        with c5: 
            amount = st.number_input("จำนวนเงินที่ขอเบิก (บาท)", min_value=0.0, format="%.2f")
            amount_text = st.text_input("จำนวนเงินตัวอักษร (เช่น หนึ่งพันบาทถ้วน)")
        with c6:
            budget_total = st.number_input("วงเงินงบประมาณทั้งโครงการ (บาท)", min_value=0.0, format="%.2f")
            budget_cat = st.selectbox("ประเภทงบประมาณ", list(BUDGET_MASTER.keys()), format_func=lambda x: f"{x} - {BUDGET_MASTER[x]}")

        st.markdown("##### ข้อมูลการสั่งจ่าย")
        c7, c8, c9 = st.columns(3)
        with c7: pay_to = st.text_input("สั่งจ่ายให้ (ระบุชื่อ/บริษัท)")
        with c8: bank_detail = st.text_input("โอนเข้าบัญชี (ธนาคาร/เลขที่)")
        with c9: 
            leader = st.text_input("ลงชื่อผู้เบิกเงิน")
            position = st.text_input("ตำแหน่ง")

        submitted = st.form_submit_button("✅ บันทึกข้อมูลและสร้างใบเบิก")

    if submitted:
        if not subject or not project:
            st.error("กรุณากรอกข้อมูลสำคัญให้ครบถ้วน")
        else:
            new_data = {
                "NO": "", "เลขที่ออก": next_doc,
                "วัน": now.day, "เดือน": now.month, "ปี": thai_year,
                "ผู้ลงนาม": "ผู้อำนวยการ", "ถึง": to_who, "เรื่อง": subject,
                "คณะ": faculty, "หัวหน้าโครงการวิจัย": leader,
                "ผู้ประสาน": "", "เงินที่อนุมัติ": budget_total,
                "จำนวนเงิน": amount, "ชื่อโครงการ": project,
                "รหัสหมวด": f"{budget_cat} {BUDGET_MASTER[budget_cat]}",
                "บันทึกเมื่อ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "สิ่งที่ส่งมาด้วย": attachments,
                "จำนวนเงิน_ตัวอักษร": amount_text,
                "สั่งจ่ายให้": pay_to,
                "ธนาคาร": bank_detail,
                "ตำแหน่ง": position
            }
            try:
                df_curr = pd.read_csv(DB_FILE)
            except: df_curr = pd.DataFrame()
            
            df_new = pd.DataFrame([new_data])
            df_out = pd.concat([df_curr, df_new], ignore_index=True)
            df_out.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

            st.success(f"บันทึกสำเร็จ! เลขที่ {next_doc}")
            
            pdf_data = new_data.copy()
            pdf_data['เดือน_ตัวอักษร'] = month_str
            st.session_state['pdf_bytes'] = create_filled_pdf(pdf_data)

    if st.session_state['pdf_bytes']:
        st.markdown("---")
        st.subheader("🖨️ พิมพ์เอกสาร")
        st.download_button("📄 ดาวน์โหลดใบเบิก (PDF)", st.session_state['pdf_bytes'], f"ใบเบิก_{next_doc.replace('/', '-')}.pdf", "application/pdf", type="primary")

# --- หน้าสรุป ---
elif menu == "📊 สรุปและคุมงบประมาณ":
    st.title("📊 ศูนย์บัญชาการงบประมาณ")
    try: raw_df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
    except: raw_df = pd.DataFrame()
    df = process_data(raw_df)

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
            if not df.empty and df['ปี'].sum() > 0:
                available_years = sorted(df[selected_col].unique(), reverse=True)
                if current_y not in available_years: available_years.insert(0, current_y)
            else: available_years = [current_y]
            selected_year = st.selectbox("2. เลือกปี (พ.ศ.)", available_years)

    st.markdown("---")
    with st.expander("⚙️ ตั้งค่าวงเงินงบประมาณ", expanded=True):
        col_set1, col_set2 = st.columns([3, 1])
        current_target = get_target_budget(selected_type_label, selected_year)
        with col_set1:
            target_input = st.number_input(f"งบประมาณรวม ({selected_type_label} {selected_year})", min_value=0.0, value=current_target, format="%.2f")
        with col_set2:
            st.write(""); st.write("")
            if st.button("💾 บันทึกยอด"):
                save_target_budget(selected_type_label, selected_year, target_input)
                st.success("บันทึกเรียบร้อย"); st.rerun()

    if not df.empty: filtered_df = df[df[selected_col] == selected_year]
    else: filtered_df = pd.DataFrame(columns=df.columns)

    total_spent = filtered_df['จำนวนเงิน'].sum()
    remaining_budget = target_input - total_spent
    percent_used = (total_spent / target_input * 100) if target_input > 0 else 0

    st.markdown("### 📈 สถานะการเบิกจ่าย")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 งบที่ได้รับ", f"{target_input:,.2f} บาท")
    m2.metric("💸 ใช้ไปแล้ว", f"{total_spent:,.2f} บาท")
    m3.metric("เหลือใช้อีก", f"{remaining_budget:,.2f} บาท", delta=f"{percent_used:.1f}% used", delta_color="normal" if remaining_budget >=0 else "inverse")
    st.progress(min(percent_used / 100, 1.0))

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("📊 สัดส่วนตามหมวดงบประมาณ")
        if not filtered_df.empty:
            cat_sum = filtered_df.groupby("รหัสหมวด")['จำนวนเงิน'].sum().reset_index()
            plot_donut_chart(cat_sum, "รหัสหมวด", "จำนวนเงิน", "สัดส่วนงบ")
            with st.expander("ดูตารางข้อมูล"): st.dataframe(cat_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else: st.info("ไม่มีข้อมูล")
    with col_chart2:
        st.subheader("🏢 สัดส่วนตามคณะ/หน่วยงาน")
        if not filtered_df.empty:
            fac_sum = filtered_df.groupby("คณะ")['จำนวนเงิน'].sum().reset_index()
            plot_donut_chart(fac_sum, "คณะ", "จำนวนเงิน", "สัดส่วนคณะ")
            with st.expander("ดูตารางข้อมูล"): st.dataframe(fac_sum.style.format({"จำนวน
