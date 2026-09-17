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

# --- 🎯 ฐานข้อมูลพิกัดข้อความ (PDF CONFIG) สอบเทียบแกน X ลงเส้นประ 100% ---
PDF_CONFIG = {
    # บรรทัด L1: หน่วยงาน (ตำแหน่งที่ถูกต้องแล้ว)
    "faculty":        (110, 675), 
    
    # บรรทัด L2: ที่ มพย. / วันที่ / เดือน / พ.ศ. (ขยับเข้าเส้นประ)
    "doc_no":         (100, 657), 
    "date_day":       (295, 657),  # ตรงกับเส้นประ วันที่
    "date_month":     (350, 657),  # ตรงกับเส้นประ เดือน
    "date_year":      (415, 657),  # ตรงกับเส้นประ พ.ศ.
    
    # บรรทัด L3: เรื่อง (กากบาทขอเบิกเงิน และ เติมข้อความ)
    "check_req":      (140,  640),  # ตรงช่องสี่เหลี่ยมเป๊ะ
    
    
    # บรรทัด L5: สิ่งที่ส่งมาด้วย 1.
    "attach_1":       (135, 613),  # ตรงเส้นประ
    
    # บรรทัด L8: ขอเบิกเงินจำนวน ... บาท ... สตางค์
    "amount":         (155, 563),  
    "amount_txt":     (330, 563),  # ลงในวงเล็บพอดี
    
    # บรรทัด L9: สั่งจ่ายให้ / โดยขอรับเงินในวันที่
    "pay_to":         (90, 547),  
    "req_d":          (275, 547),  
    "req_m":          (330, 547), 
    "req_y":          (410, 547), 
    
    # บรรทัด L11: กากบาทเข้าบัญชีธนาคาร / เลขที่
    "check_bank":     (90,  510),  # ตรงช่องสี่เหลี่ยม
    "bank_detail":    (250, 510),  # ตรงเส้นประเลขบัญชี
    
    # บรรทัด L12: เพื่อใช้ในกิจกรรมดังนี้
    "project":        (210, 495),  
    
    # บรรทัด L13: โดยใช้งบประมาณของหน่วยงาน
    "faculty_budget": (430, 130),  
    
    # บรรทัด L14: กากบาทในงบประมาณข้อ / ระบุหมวด
    "check_budget":   (130, 430),  # ตรงช่องสี่เหลี่ยม
    "budget_cat":     (235, 430),  
    
    # ส่วนลงชื่อ (ขวาล่าง)
    "leader":         (340, 303),  # กึ่งกลางวงเล็บเซ็นชื่อ
    "position":       (270, 350), 
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
        cols = [
            "NO", "เลขที่ออก", "วัน", "เดือน", "ปี", "ผู้ลงนาม", "ถึง", "เรื่อง", 
            "คณะ", "หัวหน้าโครงการวิจัย", "ผู้ประสาน", "เงินที่อนุมัติ", 
            "จำนวนเงิน", "ชื่อโครงการ", "รหัสหมวด", "บันทึกเมื่อ", 
            "สิ่งที่ส่งมาด้วย", "จำนวนเงิน_ตัวอักษร", "สั่งจ่ายให้", "ธนาคาร", "ตำแหน่ง"
        ]
        pd.DataFrame(columns=cols).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    
    if not os.path.exists(TARGET_FILE):
        pd.DataFrame(columns=["year_type", "year", "amount"]).to.csv(TARGET_FILE, index=False, encoding='utf-8-sig')
        
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
    
    df['ปีงบประมาณ'] = df.apply(lambda x: int(x['ปี']) + 1 if int(x['เดือน']) >= 8 else int(x['ปี']), axis=1)
    df['ปีการศึกษา'] = df.apply(lambda x: int(x['ปี']) if int(x['เดือน']) >= 6 else int(x['ปี']) - 1, axis=1)
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
    can.setFont(font_name, 15) 

    def draw(key, text):
        if key in PDF_CONFIG:
            base_x, base_y = PDF_CONFIG[key]
            can.drawString(base_x, base_y, str(text))

    # --- วาดข้อความลง PDF ---
    draw("faculty", data.get("คณะ", ""))
    draw("doc_no", data.get("เลขที่ออก", ""))
    draw("date_day", data["วัน"])
    draw("date_month", data["เดือน_ตัวอักษร"])
    draw("date_year", data["ปี"])
    
    draw("subject", data.get("เรื่อง", ""))
    draw("attach_1", data.get("สิ่งที่ส่งมาด้วย", "-"))
    
    can.setFont("Helvetica-Bold", 15)
    draw("check_req", "X")
    can.setFont(font_name, 15)
    
    draw("amount", f"{data['จำนวนเงิน']:,.2f}")
    draw("amount_txt", f"({data.get('จำนวนเงิน_ตัวอักษร', '')})")
    
    draw("pay_to", data.get("สั่งจ่ายให้", ""))
    draw("req_d", data["วัน"])
    draw("req_m", data["เดือน_ตัวอักษร"])
    draw("req_y", data["ปี"])
    
    if data.get("ธนาคาร", "") != "":
        can.setFont("Helvetica-Bold", 15)
        draw("check_bank", "X")
        can.setFont(font_name, 15)
        draw("bank_detail", data.get("ธนาคาร", ""))
    
    draw("project", data.get("ชื่อโครงการ", ""))
    draw("faculty_budget", data.get("คณะ", ""))
    
    can.setFont("Helvetica-Bold", 15)
    draw("check_budget", "X")
    can.setFont(font_name, 15)
    draw("budget_cat", data.get("รหัสหมวด", ""))
    
    draw("leader", data.get("หัวหน้าโครงการวิจัย", ""))
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
        with c1: 
            subject = st.text_input("เรื่อง (ขยายความจากขอเบิกเงิน)")
        with c2: 
            to_who = st.text_input("เรียน", value="หัวหน้าแผนกการเงิน")
        
        attachments = st.text_input("สิ่งที่ส่งมาด้วย (เช่น ใบเสร็จรับเงิน 3 ฉบับ)")

        c3, c4 = st.columns(2)
        with c3: 
            project = st.text_input("ใช้ในกิจกรรม (โครงการ)")
        with c4: 
            faculty = st.selectbox("หน่วยงานเจ้าของงบประมาณ", FACULTY_MASTER)

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
        with c7: 
            pay_to = st.text_input("สั่งจ่ายให้ (ระบุชื่อ/บริษัท)")
        with c8: 
            bank_detail = st.text_input("โอนเข้าบัญชีธนาคาร (ระบุชื่อธนาคารและเลขที่)")
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
            except: 
                df_curr = pd.DataFrame()
            
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
        st.download_button(
            label="📄 ดาวน์โหลดใบเบิก (PDF)", 
            data=st.session_state['pdf_bytes'], 
            file_name=f"ใบเบิก_{next_doc.replace('/', '-')}.pdf", 
            mime="application/pdf", 
            type="primary"
        )

# --- หน้าสรุป ---
elif menu == "📊 สรุปและคุมงบประมาณ":
    st.title("📊 ศูนย์บัญชาการงบประมาณ")
    try: 
        raw_df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
    except: 
        raw_df = pd.DataFrame()
        
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
                if current_y not in available_years: 
                    available_years.insert(0, current_y)
            else: 
                available_years = [current_y]
            selected_year = st.selectbox("2. เลือกปี (พ.ศ.)", available_years)

    st.markdown("---")
    with st.expander("⚙️ ตั้งค่าวงเงินงบประมาณ", expanded=True):
        col_set1, col_set2 = st.columns([3, 1])
        current_target = get_target_budget(selected_type_label, selected_year)
        with col_set1:
            target_input = st.number_input(
                f"งบประมาณรวม ({selected_type_label} {selected_year})", 
                min_value=0.0, 
                value=current_target, 
                format="%.2f"
            )
        with col_set2:
            st.write("")
            st.write("")
            if st.button("💾 บันทึกยอด"):
                save_target_budget(selected_type_label, selected_year, target_input)
                st.success("บันทึกเรียบร้อย")
                st.rerun()

    if not df.empty: 
        filtered_df = df[df[selected_col] == selected_year]
    else: 
        filtered_df = pd.DataFrame(columns=df.columns)

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
            plot_donut_chart(cat_sum, "รหัสหมวด", "จำนวนเงิน")
            with st.expander("ดูตารางข้อมูล"): 
                st.dataframe(cat_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else: 
            st.info("ไม่มีข้อมูล")
            
    with col_chart2:
        st.subheader("🏢 สัดส่วนตามคณะ/หน่วยงาน")
        if not filtered_df.empty:
            fac_sum = filtered_df.groupby("คณะ")['จำนวนเงิน'].sum().reset_index()
            plot_donut_chart(fac_sum, "คณะ", "จำนวนเงิน")
            with st.expander("ดูตารางข้อมูล"): 
                st.dataframe(fac_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else: 
            st.info("ไม่มีข้อมูล")

    if not filtered_df.empty:
        st.markdown("---")
        with open(DB_FILE, "rb") as f:
            st.download_button("📥 ดาวน์โหลดข้อมูลทั้งหมด (CSV)", f, "database_claims.csv", "text/csv")
