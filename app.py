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

# --- 🎯 ฐานข้อมูลพิกัดข้อความ (PDF CONFIG) ---
PDF_CONFIG = {
    "faculty":    (150, 740),  
    "doc_no":     (120, 715),  
    "date_day":   (380, 715),  
    "date_month": (430, 715),  
    "date_year":  (500, 715),  
    "subject":    (120, 685),  
    "to_who":     (120, 660),  
    "attach_1":   (140, 635),  
    "check_req":  (75, 605),   
    "amount":     (200, 605),  
    "amount_txt": (350, 605),  
    "pay_to":     (140, 575),  
    "req_d":      (340, 575),  
    "req_m":      (390, 575),  
    "req_y":      (470, 575),  
    "check_bank": (75, 520),   
    "bank_detail":(250, 520),  
    "project":    (210, 490),  
    "faculty_budget": (250, 460), 
    "check_budget": (75, 430), 
    "budget_cat": (180, 430),  
    "leader":     (380, 310),  
    "position":   (380, 285),  
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
    df['เดือน'] = pd.to_numeric(df['เดือน'], errors='coerce').fillna(0).astype
