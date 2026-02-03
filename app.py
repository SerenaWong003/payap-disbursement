import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. ตั้งค่าระบบ ---
st.set_page_config(page_title="ระบบทะเบียนคุมตั้งเบิก มพย.", layout="centered", page_icon="🛡️")
now = datetime.now()
thai_year = now.year + 543
current_date_str = now.strftime(f"%d/%m/{thai_year}")
DB_FILE = "database_claims.csv"

# --- 2. ฟังก์ชันจัดการเลขที่ (ตัดรอบทุก 1 ม.ค.) ---
def get_next_doc_no():
    if not os.path.exists(DB_FILE):
        return "0203/001"
    try:
        df = pd.read_csv(DB_FILE)
        if df.empty: return "0203/001"
        last_year = int(df['ปี'].iloc[-1])
        if thai_year > last_year: return "0203/001"
        last_doc = str(df['เลขที่ออก'].iloc[-1])
        new_num = int(last_doc.split('/')[-1]) + 1
        return f"0203/{new_num:03d}"
    except:
        return "0203/001"

# --- 3. ส่วน UI ---
st.title("🛡️ ระบบออกเลขที่เอกสารเบิกจ่ายของสำนักวิจัย")
st.info(f"📅 วันที่: {current_date_str} | ปี พ.ศ. {thai_year}")

next_doc = get_next_doc_no()
st.subheader(f"เลขที่เอกสารที่จะออก: :blue[{next_doc}]")

with st.form("main_form", clear_on_submit=True):
    subject = st.text_input("เรื่อง (Subject)")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("ชื่อโครงการวิจัย")
        total_budget = st.number_input("งบประมาณทั้งโครงการ", min_value=0.0, format="%.2f")
        faculty = st.text_input("คณะ / หน่วยงาน")
    with col2:
        leader_name = st.text_input("ชื่อหัวหน้าโครงการ")
        claim_amount = st.number_input("จำนวนเงินที่เบิกครั้งนี้", min_value=0.0, format="%.2f")
        budget_code = st.text_input("รหัสหมวดงบประมาณ")
    
    to_person = st.text_input("เรียน", value="รองอธิการบดีฝ่ายวิชาการและวิจัย,ผู้อำนวยการสำนักการเงิน")
    submit = st.form_submit_button("✅ บันทึกและออกเลขที่")

if submit:
    new_row = {
        "NO": "", "เลขที่ออก": next_doc, "วัน": now.day, "เดือน": now.month, "ปี": thai_year,
        "ผู้ลงนาม": "ผู้อำนวยการ", "ถึง": to_person, "เรื่อง": subject, "คณะ": faculty,
        "หัวหน้าโครงการวิจัย": leader_name, "ผู้ประสาน": "", "เงินที่อนุมัติ": total_budget,
        "จำนวนเงิน": claim_amount, "ชื่อโครงการ": project_name, "รหัสหมวด": budget_code,
        "บันทึกเมื่อ": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    df_new = pd.DataFrame([new_row])
    file_exists = os.path.isfile(DB_FILE)
    df_new.to_csv(DB_FILE, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')
    st.success(f"บันทึกเลขที่ {next_doc} สำเร็จ!")
    st.balloons()

# --- 4. ปุ่ม Export (Sidebar) ---
st.sidebar.title("📊 ฐานข้อมูล")
if os.path.exists(DB_FILE):
    df_db = pd.read_csv(DB_FILE)
    st.sidebar.write(f"รายการทั้งหมด: {len(df_db)}")
    with open(DB_FILE, "rb") as f:
        st.sidebar.download_button("📥 Export CSV (Excel)", f, f"เบิกจ่าย_{thai_year}.csv", "text/csv")
