import streamlit as st
import pandas as pd
from datetime import datetime
import os
import matplotlib.pyplot as plt

# --- 1. ตั้งค่าระบบ ---
st.set_page_config(page_title="ระบบบริหารจัดการงบประมาณ มพย.", layout="wide", page_icon="🛡️")

# รองรับภาษาไทยในกราฟ Matplotlib (ใช้ Font ภาษาอังกฤษแทนเพื่อป้องกันสระลอย หรือใช้ Tahoma ถ้ามี)
# เนื่องจาก Server Streamlit อาจไม่มีฟอนต์ไทย จั่นเจาจะใช้เทคนิคแสดงผลเป็นรหัสหรือภาษาอังกฤษกำกับ
# หรือใช้ Default Font ที่อ่านง่าย

DB_FILE = "database_claims.csv"
TARGET_FILE = "budget_targets.csv"

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
    "บัณฑิตวิทยาลัย", "สำนักการศึกษาทั่วไป"
]

# --- 2. ฟังก์ชันจัดการข้อมูล ---

def init_files():
    if not os.path.exists(DB_FILE):
        cols = ["NO", "เลขที่ออก", "วัน", "เดือน", "ปี", "ผู้ลงนาม", "ถึง", "เรื่อง", 
                "คณะ", "หัวหน้าโครงการวิจัย", "ผู้ประสาน", "เงินที่อนุมัติ", 
                "จำนวนเงิน", "ชื่อโครงการ", "รหัสหมวด", "บันทึกเมื่อ"]
        pd.DataFrame(columns=cols).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    
    if not os.path.exists(TARGET_FILE):
        pd.DataFrame(columns=["year_type", "year", "amount"]).to_csv(TARGET_FILE, index=False, encoding='utf-8-sig')

def get_current_date():
    now = datetime.now()
    thai_year = now.year + 543
    return now, thai_year, now.strftime(f"%d/%m/{thai_year}")

def get_next_doc_no():
    try:
        if not os.path.exists(DB_FILE): return "0203/001"
        df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
        if df.empty: return "0203/001"
        
        df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
        _, current_year, _ = get_current_date()
        
        if current_year > df['ปี'].max():
            return "0203/001"
            
        last_doc = str(df['เลขที่ออก'].iloc[-1])
        if "/" in last_doc:
            return f"0203/{int(last_doc.split('/')[-1]) + 1:03d}"
        return "0203/001"
    except:
        return "0203/001"

def process_data(df):
    if df.empty: return df
    df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
    df['เดือน'] = pd.to_numeric(df['เดือน'], errors='coerce').fillna(0).astype(int)
    df['จำนวนเงิน'] = pd.to_numeric(df['จำนวนเงิน'], errors='coerce').fillna(0.0)

    df['ปีงบประมาณ'] = df.apply(lambda x: x['ปี'] + 1 if x['เดือน'] >= 8 else x['ปี'], axis=1)
    df['ปีการศึกษา'] = df.apply(lambda x: x['ปี'] if x['เดือน'] >= 6 else x['ปี'] - 1, axis=1)
    df['ปีปฏิทิน'] = df['ปี']
    return df

def get_target_budget(year_type, year):
    if not os.path.exists(TARGET_FILE): return 0.0
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

def plot_pie_chart(data, label_col, value_col, title):
    """สร้างกราฟ Pie Chart ที่ Copy ได้"""
    if data.empty:
        st.info("ไม่มีข้อมูลสำหรับแสดงกราฟ")
        return

    # เตรียมข้อมูล
    labels = data[label_col].astype(str).values
    sizes = data[value_col].values
    
    # สร้างกราฟ
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # สีโทนฟ้า-น้ำเงิน (Payap Theme)
    colors = plt.cm.Blues([0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=None, # ปิด label รอบนอกเพื่อความสะอาด
        autopct='%1.1f%%', 
        startangle=90, 
        colors=colors,
        pctdistance=0.85
    )
    
    # วาดวงกลมตรงกลางให้เป็น Donut Chart (ดูทันสมัยขึ้น)
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig.gca().add_artist(centre_circle)
    
    ax.axis('equal')  
    plt.title(title, fontsize=14, fontfamily='sans-serif')
    plt.legend(wedges, labels, title="รายการ", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    
    st.pyplot(fig) # แสดงผลเป็นรูปภาพ

# --- เริ่มต้นระบบ ---
init_files()

# --- 3. ส่วนแสดงผล (UI) ---
st.sidebar.title("🛡️ เมนูหลัก")
menu = st.sidebar.radio("เลือกเมนู", ["📝 บันทึกตั้งเบิก", "📊 สรุปและคุมงบประมาณ"])

st.sidebar.markdown("---")
if st.sidebar.button("⚠️ ล้างฐานข้อมูลทั้งหมด"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(TARGET_FILE): os.remove(TARGET_FILE)
    init_files()
    st.sidebar.success("ล้างข้อมูลเรียบร้อย")
    st.rerun()

# ==========================================
# หน้า 1: บันทึกตั้งเบิก
# ==========================================
if menu == "📝 บันทึกตั้งเบิก":
    now, thai_year, date_str = get_current_date()
    st.title(f"📝 บันทึกขออนุมัติเบิกจ่าย")
    
    next_doc = get_next_doc_no()
    st.info(f"เลขที่เอกสารปัจจุบัน: **{next_doc}** | วันที่: {date_str}")

    with st.form("entry_form", clear_on_submit=True):
        col_topic, col_to = st.columns([2, 1])
        with col_topic:
            subject = st.text_input("เรื่อง")
        with col_to:
            to_who = st.text_input("เรียน", value="รองอธิการบดีฝ่ายวิชาการและวิจัย")
            
        c1, c2 = st.columns(2)
        with c1:
            project = st.text_input("ชื่อโครงการวิจัย")
            budget_total = st.number_input("งบประมาณโครงการ (บาท)", min_value=0.0, format="%.2f")
            faculty = st.selectbox("คณะ / หน่วยงาน", FACULTY_MASTER)
        with c2:
            leader = st.text_input("ชื่อหัวหน้าโครงการ")
            amount = st.number_input("ยอดเบิกครั้งนี้ (บาท)", min_value=0.0, format="%.2f")
            budget_cat = st.selectbox("หมวดงบประมาณ", list(BUDGET_MASTER.keys()), format_func=lambda x: f"{x} - {BUDGET_MASTER[x]}")

        if st.form_submit_button("✅ บันทึกข้อมูล"):
            if not subject or not project:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            else:
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
                st.rerun()

# ==========================================
# หน้า 2: สรุปและคุมงบประมาณ
# ==========================================
elif menu == "📊 สรุปและคุมงบประมาณ":
    st.title("📊 ศูนย์บัญชาการงบประมาณ")
    
    try:
        raw_df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
    except:
        raw_df = pd.DataFrame()
        
    df = process_data(raw_df)

    # --- Filter ---
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
            if not df.empty:
                available_years = sorted(df[selected_col].unique(), reverse=True)
                if current_y not in available_years: available_years.insert(0, current_y)
            else:
                available_years = [current_y]
                
            selected_year = st.selectbox("2. เลือกปี (พ.ศ.)", available_years)

    st.markdown("---")

    # --- Budget Setting ---
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
                st.success("บันทึกเรียบร้อย")
                st.rerun()

    # --- Metrics ---
    filtered_df = df[df[selected_col] == selected_year]
    total_spent = filtered_df['จำนวนเงิน'].sum()
    remaining_budget = target_input - total_spent
    percent_used = (total_spent / target_input * 100) if target_input > 0 else 0

    st.markdown("### 📈 สถานะการเบิกจ่าย")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 งบที่ได้รับ", f"{target_input:,.2f} บาท")
    m2.metric("💸 ใช้ไปแล้ว", f"{total_spent:,.2f} บาท")
    m3.metric("เหลือใช้อีก", f"{remaining_budget:,.2f} บาท", delta=f"{percent_used:.1f}% used", delta_color="normal" if remaining_budget >=0 else "inverse")
    
    st.progress(min(percent_used / 100, 1.0))

    # --- Charts (Pie Chart) ---
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📊 สัดส่วนตามหมวดงบประมาณ")
        if not filtered_df.empty:
            cat_sum = filtered_df.groupby("รหัสหมวด")['จำนวนเงิน'].sum().reset_index()
            # ใช้ฟังก์ชันสร้าง Pie Chart ที่ก๊อบปี้รูปได้
            plot_pie_chart(cat_sum, "รหัสหมวด", "จำนวนเงิน", "สัดส่วนการใช้งบแยกตามหมวด")
            
            # ตารางข้อมูลประกอบ
            with st.expander("ดูตารางข้อมูล"):
                st.dataframe(cat_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else:
            st.info("ไม่มีข้อมูล")

    with col_chart2:
        st.subheader("🏢 สัดส่วนตามคณะ/หน่วยงาน")
        if not filtered_df.empty:
            fac_sum = filtered_df.groupby("คณะ")['จำนวนเงิน'].sum().reset_index()
            plot_pie_chart(fac_sum, "คณะ", "จำนวนเงิน", "สัดส่วนการใช้งบแยกตามคณะ")
            
            with st.expander("ดูตารางข้อมูล"):
                st.dataframe(fac_sum.style.format({"จำนวนเงิน": "{:,.2f}"}), hide_index=True)
        else:
            st.info("ไม่มีข้อมูล")

    # Download
    if not filtered_df.empty:
        st.markdown("---")
        with open(DB_FILE, "rb") as f:
            st.download_button("📥 ดาวน์โหลดข้อมูลทั้งหมด (CSV)", f, "database_claims.csv", "text/csv")
