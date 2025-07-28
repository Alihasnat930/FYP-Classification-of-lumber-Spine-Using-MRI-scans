import streamlit as st
import requests
from datetime import datetime
from typing import Optional
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
import os
import base64

 
st.set_page_config(page_title="Med Bot - Spine MRI Reports", page_icon="🩺", layout="wide")
 
st.markdown("""
<style>
:root {
    --primary: #2563eb;
    --secondary: #10b981;
    --dark-bg: #0f172a;
    --card-bg: #1e293b;
}

.metric-card {
    background-color: var(--card-bg);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    border-left: 4px solid var(--primary);
}

.patient-card {
    background-color: var(--card-bg);
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
    border-left: 4px solid var(--secondary);
}

.stButton>button {
    background-color: var(--primary) !important;
    color: white !important;
    border-radius: 8px !important;
}

.stButton>button:hover {
    background-color: var(--secondary) !important;
}
</style>
""", unsafe_allow_html=True)
 
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

API_URL = "http://127.0.0.1:8000"   

 
def make_api_request(method: str, endpoint: str, token: Optional[str] = None, **kwargs):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            headers=headers,
            timeout=10,
            **kwargs
        )
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def login(username: str, password: str):
    return make_api_request("POST", "/token", data={"username": username, "password": password})

def register(username: str, email: str, password: str):
    return make_api_request("POST", "/register", json={"username": username, "email": email, "password": password})

def analyze_mri(file, token: str, model_choice: str = "v1"):
    files = {"file": (file.name, file.getvalue())}
    return make_api_request("POST", "/analyze", token=token, files=files, params={"model_choice": model_choice})

def create_report(token: str, report_data: dict):
    return make_api_request("POST", "/report/create", token=token, json=report_data)

def get_reports(token: str):
    return make_api_request("GET", "/report", token=token) or []

def email_report(token: str, report_id: int, email_to: str):
    return make_api_request("POST", f"/report/{report_id}/email", token=token, json={"email_to": email_to})

 
def metric_card(title: str, value: str):
    st.markdown(f"""
    <div class="metric-card">
        <div>{title}</div>
        <div style="font-size: 24px; font-weight: bold;">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def patient_card(name: str, date: str, findings: str):
    st.markdown(f"""
    <div class="patient-card">
        <strong>{name}</strong> ({date})<br>
        <div style="color: #94a3b8; margin-top: 5px;">{findings[:100]}...</div>
    </div>
    """, unsafe_allow_html=True)

 
def main():
    st.sidebar.image("https://img.icons8.com/fluency/96/medical-doctor.png", width=80)
    st.sidebar.title("Med Bot")

    # Initialize session state
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None

    # Navigation
    if st.session_state.token:
        nav = st.sidebar.radio("Menu", ["Dashboard", "Upload & Analyze", "Reports", "Email Report","Settings"])
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout"):
            st.session_state.token = None
            st.session_state.username = None
            st.rerun()
    else:
        nav = "Login"

 
    if nav == "Login":
        login_page()
    elif nav == "Dashboard":
        dashboard_page()
    elif nav == "Upload & Analyze":
        upload_page()
    elif nav == "Reports":
        reports_page()
    elif nav == "Email Report":
        email_page()
    elif nav == "Settings":
        settings()

def login_page():
    st.header("🔐 Authentication")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                result = login(username, password)
                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Login failed")

    with tab2:
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Register"):
                if password != confirm:
                    st.error("Passwords don't match")
                else:
                    result = register(username, email, password)
                    if result and "msg" in result:
                        st.success("Registration successful! Please login")
                    else:
                        st.error("Registration failed")

def dashboard_page():
    st.header("📊 Dashboard Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Recent Scans", "5")
    with col2:
        metric_card("Reports Generated", "12")
    with col3:
        metric_card("Emails Sent", "8")
    
    st.info("✨ 3 new reports ready for review", icon="💡")
    st.divider()
     
    st.subheader("Recent Patients")
    reports = get_reports(st.session_state.token)
    if reports:
        for report in reports[:3]:
            patient_card(
                report.get("patient_name", "N/A"),
                report.get("exam_date", "N/A"),
                report.get("findings", "No findings")
            )
    else:
        st.info("No reports found. Upload an MRI to get started")


def delete_report(token: str, report_id: int):
    return make_api_request("DELETE", f"/report/{report_id}", token=token)

def reports_page():
    st.header("📋 Patient Reports")
    reports = get_reports(st.session_state.token)

    if reports:
        search_query = st.text_input("Search Reports")

        filtered_reports = [
            r for r in reports 
            if search_query.lower() in r.get("patient_name", "").lower() or 
               search_query in r.get("exam_date", "")
        ] if search_query else reports

        for report in filtered_reports:
            with st.expander(f"{report.get('patient_name', 'N/A')} - {report.get('exam_date', 'N/A')}"):
                col1, col2 = st.columns([3,1])
                with col1:
                    st.markdown(f"**History:** {report.get('history', '')}")
                    st.markdown(f"**Technique:** {report.get('technique', '')}")
                    st.markdown(f"**Findings:** {report.get('findings', '')}")
                    st.markdown(f"**Created:** {report.get('created_at', '')}")
                with col2:
                    if st.button("Generate Full Report", key=f"pdf_{report.get('id', '')}"):
                        buffer = io.BytesIO()
                        c = canvas.Canvas(buffer, pagesize=letter)
                        width, height = letter

                        left_margin = 50
                        right_margin = 50
                        top_margin = 50
                        content_width = width - left_margin - right_margin

                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(width/2, height - top_margin, "SPINE MRI RADIOLOGY REPORT")
                        c.line(left_margin, height - top_margin - 10, width - right_margin, height - top_margin - 10)
                        current_y = height - top_margin - 40

                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(left_margin, current_y, "PATIENT INFORMATION:")
                        current_y -= 20
                        c.setFont("Helvetica", 10)
                        patient_info = [
                            f"Name: {report.get('patient_name', 'N/A')}",
                            f"Exam Date: {report.get('exam_date', 'N/A')}",
                            f"Report Date: {datetime.now().strftime('%Y-%m-%d')}",
                            f"MRN: 123456",
                            f"DOB: 1980-01-01"
                        ]
                        for info in patient_info:
                            c.drawString(left_margin, current_y, info)
                            current_y -= 15
                        current_y -= 10

                        # Clinical History
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(left_margin, current_y, "CLINICAL HISTORY:")
                        current_y -= 20
                        c.setFont("Helvetica", 10)
                        history = report.get('history', 'No clinical history provided.')
                        history_lines = []
                        words = history.split()
                        line = ""
                        for word in words:
                            if c.stringWidth(line + word, "Helvetica", 10) < content_width:
                                line += word + " "
                            else:
                                history_lines.append(line)
                                line = word + " "
                        if line:
                            history_lines.append(line)
                        for line in history_lines:
                            c.drawString(left_margin, current_y, line)
                            current_y -= 15
                        current_y -= 10

                        # Technique
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(left_margin, current_y, "TECHNIQUE:")
                        current_y -= 20
                        c.setFont("Helvetica", 10)
                        technique = report.get('technique', 'MRI lumbar spine without contrast.')
                        c.drawString(left_margin, current_y, technique)
                        current_y -= 15
                        current_y -= 10

                        # Comparison
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(left_margin, current_y, "COMPARISON:")
                        current_y -= 20
                        c.setFont("Helvetica", 10)
                        comparison = "No prior studies available for comparison."
                        c.drawString(left_margin, current_y, comparison)
                        current_y -= 15
                        current_y -= 10

                        # Findings
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(left_margin, current_y, "FINDINGS:")
                        current_y -= 20
                        c.setFont("Helvetica", 10)
                        findings = report.get('findings', 'No significant findings.')
                        findings_lines = []
                        words = findings.split()
                        line = ""
                        for word in words:
                            if c.stringWidth(line + word, "Helvetica", 10) < content_width:
                                line += word + " "
                            else:
                                findings_lines.append(line)
                                line = word + " "
                        if line:
                            findings_lines.append(line)
                        for line in findings_lines:
                            c.drawString(left_margin, current_y, line)
                            current_y -= 15
                        current_y -= 10

                        # Impression
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(left_margin, current_y, "IMPRESSION:")
                        current_y -= 20
                        c.setFont("Helvetica", 10)
                        impression = "1. " + (findings.split('.')[0] if findings else "No significant abnormality detected.")
                        c.drawString(left_margin, current_y, impression)
                        current_y -= 15
 
                        # Image
                        img_base64 = report.get("image_base64")
                        if img_base64:
                            try:
                                img_bytes = base64.b64decode(img_base64)
                                img = Image.open(io.BytesIO(img_bytes))
                                img.thumbnail((300, 300))  # Resize
                                img_io = io.BytesIO()
                                img.save(img_io, format="PNG")
                                img_io.seek(0)

                                img_width = 200
                                img_height = 200 * (img.size[1] / img.size[0]) if img.size[0] > 0 else 200
                                image_x = (width - img_width) / 2

                                c.drawImage(ImageReader(img_io),
                                            image_x,
                                            current_y - img_height,
                                            width=img_width,
                                            height=img_height)

                                c.setFont("Helvetica-Oblique", 8)
                                c.drawString(image_x,
                                            current_y - img_height - 15,
                                            "Figure 1: MRI of lumbar spine")

                                current_y -= (img_height + 25)

                            except Exception as e:
                                st.error(f"Error loading image from base64: {str(e)}")
 

                        # Footer
                        c.setFont("Helvetica-Oblique", 8)
                        c.drawString(left_margin, 30, "This report was generated by MedBot AI Radiology Assistant")
                        c.drawString(width - right_margin - 150, 30, datetime.now().strftime("%Y-%m-%d %H:%M"))
                        c.save()
                        buffer.seek(0)

                        st.download_button(
                            label="Download Full Report PDF",
                            data=buffer,
                            file_name=f"Spine_MRI_Report_{report.get('patient_name', 'report')}.pdf",
                            mime="application/pdf"
                        )
                    if st.button("Delete Report", key=f"del_{report.get('id', '')}"):
                        delete_result = delete_report(st.session_state.token, report.get("id"))
                        if delete_result is not None:
                            st.success("Report deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete report.")
    else:
        st.info("No reports found. Analyze an MRI to generate reports")

def upload_page():
    st.header("🖼️ MRI Analysis")

    # Initialize session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
        st.session_state.analysis_patient_name = ""
        st.session_state.analysis_exam_date = None
        st.session_state.analysis_uploaded_file = None
        st.session_state.analysis_model_choice = "v1"

    with st.form("upload_form"):
        patient_name = st.text_input("Patient Name", value=st.session_state.analysis_patient_name)
        exam_date = st.date_input("Exam Date", value=st.session_state.analysis_exam_date or datetime.now())
        uploaded_file = st.file_uploader("Upload MRI Scan", type=["jpg", "jpeg", "png"])
        model_choice = st.radio("Model Version", ["v1", "v2"], horizontal=True, index=0 if st.session_state.analysis_model_choice == "v1" else 1)
        analyze = st.form_submit_button("Analyze")

        if analyze:
            if uploaded_file:
                with st.spinner("Analyzing MRI..."):
                    result = analyze_mri(uploaded_file, st.session_state.token, model_choice)
                if result:
                    st.session_state.analysis_result = result
                    st.session_state.analysis_patient_name = patient_name
                    st.session_state.analysis_exam_date = exam_date
                    st.session_state.analysis_uploaded_file = uploaded_file
                    st.session_state.analysis_model_choice = model_choice
                    st.success("Analysis Complete! Scroll down to save the report.")
                else:
                    st.error("Analysis failed")
            else:
                st.warning("Please upload an MRI file")

    # Display results and allow saving
    if st.session_state.analysis_result:
        st.image(st.session_state.analysis_uploaded_file, width=300)
        with st.expander("Diagnosis Details"):
            st.markdown(f"**Patient:** {st.session_state.analysis_patient_name}")
            st.markdown(f"**Exam Date:** {st.session_state.analysis_exam_date}")
            st.divider()
            st.subheader("Findings")
            st.markdown(st.session_state.analysis_result.get("text_summary", ""))

        if st.button("Save Report"):
            uploaded_file = st.session_state.analysis_uploaded_file
            img_base64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8") if uploaded_file else None

            report_data = {
                "patient_name": st.session_state.analysis_patient_name,
                "exam_date": st.session_state.analysis_exam_date.isoformat(),
                "history": st.session_state.analysis_result.get("history", ""),
                "technique": st.session_state.analysis_result.get("technique", ""),
                "findings": st.session_state.analysis_result.get("text_summary", ""),
                "image_base64": img_base64
            }

            result = create_report(st.session_state.token, report_data)
            if result:
                st.success("Report saved successfully!") 
                st.session_state.analysis_result = None
                st.session_state.analysis_patient_name = ""
                st.session_state.analysis_exam_date = None
                st.session_state.analysis_uploaded_file = None
                st.session_state.analysis_model_choice = "v1"
            else:
                st.error("Failed to save report")


def email_page():
    st.header("📧 Send Report to Doctor")
    reports = get_reports(st.session_state.token)

    if reports:
        report_options = {
            f"{r.get('patient_name', 'N/A')} ({r.get('exam_date', 'N/A')})": r.get("id")
            for r in reports
        }

        selected = st.selectbox("Select Report to Send", options=list(report_options.keys()))
        doctor_email = st.text_input("Doctor's Email Address")

        if st.button("Send Report"):
            report_id = report_options[selected]
            success = send_report_from_server(
                st.session_state.token,
                report_id,
                doctor_email
            )

            if success:
                st.success(f"Report sent to {doctor_email}")
            else:
                st.error("Failed to send report")
    else:
        st.info("No reports available to send")

def send_report_from_server(token, report_id, email_to):
    url = f"{API_URL}/report/{report_id}/email"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"email_to": email_to}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        return response.status_code == 200
    except requests.RequestException as e:
        st.error(f"Failed to send email: {e}")
        return False
    
def settings():
    st.header("⚙️ Settings")
    st.subheader("Change Password")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("Change Password"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            else: 
                result = make_api_request(
                    "POST",
                    "/change-password",
                    token=st.session_state.token,
                    json={
                        "current_password": current_password,
                        "new_password": new_password
                    }
                )
            if result and result.get("msg") == "Password changed successfully":
             st.success("Password changed successfully")
            elif result and "detail" in result:
             st.error(result["detail"])
            else:
             st.error("Failed to change password")
    st.subheader("Delete Account")
    with st.form("delete_account_form"):
        confirm = st.checkbox("I confirm I want to delete my account")
        
        if st.form_submit_button("Delete Account"):
            if not st.session_state.token:
                st.error("You must be logged in to delete your account.")
            elif confirm:
                result = make_api_request(
                    "DELETE",
                    "/delete-account",
                    token=st.session_state.token
                ) 
                if result and result.get("msg") == "Account deleted successfully":
                    st.success("Account deleted successfully")
                    st.toast("Your account has been deleted.", icon="✅")
                    st.session_state.token = None
                    st.session_state.username = None
                    st.rerun()
                elif result is None:
                    st.error("Unauthorized. Please log in again.")
                    st.session_state.token = None
                    st.session_state.username = None
                    st.rerun()
                else:
                    st.error("Failed to delete account")
            else:
                st.warning("Please confirm to delete your account")

if __name__ == "__main__":
    main()