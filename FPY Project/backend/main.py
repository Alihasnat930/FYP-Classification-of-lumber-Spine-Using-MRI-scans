from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session
import models
import crud
from database import SessionLocal, engine
import base64
from pydantic import BaseModel
from fastapi import Form
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from settings import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import io
from fastapi import Path  

# === Init DB ===
models.Base.metadata.create_all(bind=engine)

# === Load Models === 
try:
    model_v1 = load_model("mvc_best.h5")
    model_v2 = load_model("mvc_ofit.h5")
except Exception as e:
    print(f"Error loading models: {e}") 
    model_v1 = None
    model_v2 = None


label_cols = [
    "left_neural_foraminal_narrowing",
    "right_neural_foraminal_narrowing",
    "left_subarticular_stenosis",
    "right_subarticular_stenosis",
    "spinal_canal_stenosis"
]

severity_labels = ["Normal/Mild", "Moderate", "Severe"]

explanation_map = {
    "left_neural_foraminal_narrowing": {
        "name": "Left Foraminal Narrowing",
        "category": "Nerve Root Impingement",
        "explanations": [
            "Normal or slight narrowing on the left.",
            "Moderate narrowing on the left may cause tingling.",
            "Severe narrowing can compress nerves and cause pain."
        ]
    },
    "right_neural_foraminal_narrowing": {
        "name": "Right Foraminal Narrowing",
        "category": "Nerve Root Impingement",
        "explanations": [
            "Normal or slight narrowing on the right.",
            "Moderate narrowing on the right may cause tingling.",
            "Severe narrowing can compress nerves and cause pain."
        ]
    },
    "left_subarticular_stenosis": {
        "name": "Left Subarticular Stenosis",
        "category": "Spinal Stenosis",
        "explanations": [
            "Normal or mild narrowing of the left subarticular zone.",
            "Moderate narrowing of the left subarticular zone.",
            "Severe narrowing of the left subarticular zone."
        ]
    },
    "right_subarticular_stenosis": {
        "name": "Right Subarticular Stenosis",
        "category": "Spinal Stenosis",
        "explanations": [
            "Normal or mild narrowing of the right subarticular zone.",
            "Moderate narrowing of the right subarticular zone.",
            "Severe narrowing of the right subarticular zone."
        ]
    },
    "spinal_canal_stenosis": {
        "name": "Spinal Canal Stenosis",
        "category": "Central Canal",
        "explanations": [
            "Normal or mild narrowing of the spinal canal.",
            "Moderate narrowing of the spinal canal.",
            "Severe narrowing of the spinal canal."
        ]
    }
}

# === Auth Setup ===
SECRET_KEY = "SomeSecretKeyThatIsVeryLongAndSecure"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# === Pydantic Models ===
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class ReportCreate(BaseModel):
    patient_name: str
    exam_date: str
    history: str
    technique: str
    findings: str
    image_base64: Optional[str] = None  

class ReportOut(ReportCreate):
    id: int
    created_by: str
    created_at: datetime 

class EmailRequest(BaseModel):
    email_to: str

class SupportRequest(BaseModel):
    email: str
    message: str

class ExportRequest(BaseModel):
    report_id: int
    format: str   

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# === Utility Functions ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    user = crud.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found", headers={"WWW-Authenticate": "Bearer"})
    return user

# === Image Processing ===
def preprocess(img_bytes):
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    img = img.resize((224, 224))
    img_array = image.img_to_array(img) / 255.0
    return np.expand_dims(img_array, axis=0).astype(np.float32)

def model_predict(img_input, model):
    if model is None:
        raise HTTPException(status_code=500, detail="AI model not loaded. Please check server logs.")
    preds = model.predict([img_input, img_input, img_input])
    preds = np.squeeze(preds)
    return preds

def generate_history_text(diagnosis): 
    return "Patient presents with symptoms consistent with: " + ", ".join(
        [f"{explanation_map[k]['name']}: {v}" for k, v in diagnosis.items()]
    )

def generate_technique_text():
    return "MRI lumbar spine without contrast."

# === FastAPI App ===
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    hashed_pw = get_password_hash(user.password)
    db_user = crud.create_user(db, username=user.username, email=user.email, hashed_password=hashed_pw)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    return {"msg": "User registered successfully"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password", headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), model_choice: str = Query("v1"), current_user=Depends(get_current_user)):
    if model_v1 is None or model_v2 is None:
        raise HTTPException(status_code=500, detail="AI models are not loaded on the server.")

    img_bytes = await file.read()
    img_input = preprocess(img_bytes)
    
    model = None
    if model_choice == "v1":
        model = model_v1
    elif model_choice == "v2":
        model = model_v2
    else:
        raise HTTPException(status_code=400, detail="Invalid model choice. Must be 'v1' or 'v2'.")

    preds = model_predict(img_input, model)

    decoded = {}
    summary = []

    for i, label in enumerate(label_cols):
        idx = int(np.argmax(preds[i]))
        severity = severity_labels[idx]
        decoded[label] = severity
        summary.append(f"{explanation_map[label]['name']} ({explanation_map[label]['category']}): {severity} - {explanation_map[label]['explanations'][idx]}")
 
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    return {
        "diagnosis": decoded,
        "text_summary": "\n".join(summary),
        "history": generate_history_text(decoded),
        "technique": generate_technique_text(),
        "raw_output": preds.tolist(),
        "image_shape": img_input.shape,
        "image_base64": img_base64,  
        "image_filename": file.filename,
        "image_content_type": file.content_type
    }

@app.post("/report/create", response_model=ReportOut)
def create_report(report: ReportCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)): 
    db_report = crud.create_report(db, report, current_user.username)
    if not db_report:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create report")
    return db_report

@app.get("/report", response_model=List[ReportOut])
def get_reports(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return crud.get_reports_by_user(db, current_user.username)

@app.get("/report/{report_id}", response_model=ReportOut)
def get_report(report_id: int = Path(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    report = crud.get_report_by_id(db, report_id, current_user.username)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report

@app.post("/report/{report_id}/email", status_code=status.HTTP_200_OK)
def email_report(
    req: EmailRequest,
    report_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    report = crud.get_report_by_id(db, report_id, current_user.username)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    left_margin = 50
    right_margin = 50
    top_margin = 50
    content_width = width - left_margin - right_margin
    current_y = height - top_margin

    # PDF Header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, current_y, "SPINE MRI RADIOLOGY REPORT")
    current_y -= 10
    c.line(left_margin, current_y, width - right_margin, current_y)
    current_y -= 30

    # Patient Info  
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, current_y, "PATIENT INFORMATION:")
    current_y -= 20
    c.setFont("Helvetica", 10)
    patient_info = [
        f"Name: {report.patient_name}",
        f"Exam Date: {report.exam_date}",
        f"Report Date: {datetime.now().strftime('%Y-%m-%d')}",
        f"MRN: 123456",  
        f"DOB: 1980-01-01"  
    ]
    for info in patient_info:
        c.drawString(left_margin, current_y, info)
        current_y -= 15
    current_y -= 10
 
    def draw_wrapped_text(canvas_obj, text, x_start, y_start, max_width, font_name="Helvetica", font_size=10, line_height=15):
        canvas_obj.setFont(font_name, font_size)
        words = text.split()
        line = ""
        current_line_y = y_start
        for word in words:
            if canvas_obj.stringWidth(line + word + " ", font_name, font_size) < max_width:
                line += word + " "
            else:
                canvas_obj.drawString(x_start, current_line_y, line.strip())
                current_line_y -= line_height
                line = word + " "
        if line:
            canvas_obj.drawString(x_start, current_line_y, line.strip())
            current_line_y -= line_height
        return current_line_y

    # Clinical History 
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, current_y, "CLINICAL HISTORY:")
    current_y = draw_wrapped_text(c, report.history, left_margin, current_y - 20, content_width)
    current_y -= 10   

    # Technique  
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, current_y, "TECHNIQUE:")
    current_y = draw_wrapped_text(c, report.technique, left_margin, current_y - 20, content_width)
    current_y -= 10

    # Comparison  
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, current_y, "COMPARISON:")
    current_y = draw_wrapped_text(c, "No prior studies available for comparison." if not report.history else "Comparison with previous studies not available.", left_margin, current_y - 20, content_width)
    current_y -= 10

    # Findings 
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, current_y, "FINDINGS:")
    current_y = draw_wrapped_text(c, report.findings, left_margin, current_y - 20, content_width)
    current_y -= 10

    # Impression 
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, current_y, "IMPRESSION:")
    impression_text = "1. " + (report.findings.split('.')[0] if report.findings else "No significant abnormality detected.")
    current_y = draw_wrapped_text(c, impression_text, left_margin, current_y - 20, content_width)
    current_y -= 10

    # IMAGE HANDLING  
    if report.image_base64:
        try: 
            img_bytes = base64.b64decode(report.image_base64)
            img = Image.open(io.BytesIO(img_bytes))
              
            max_img_width = content_width / 2  
            max_img_height = 200  
            
            original_width, original_height = img.size
            aspect_ratio = original_width / original_height

            img_width = min(max_img_width, original_width)
            img_height = img_width / aspect_ratio

            if img_height > max_img_height:
                img_height = max_img_height
                img_width = img_height * aspect_ratio
             
            if img_width > content_width:
                img_width = content_width
                img_height = img_width / aspect_ratio
 
            img_io = io.BytesIO()
            img.save(img_io, format="PNG")
            img_io.seek(0)  
 
            image_x = left_margin + (content_width - img_width) / 2
             
            if current_y - img_height - 30 < 50:  
                c.showPage()  
                current_y = height - top_margin  
                 
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(width / 2, current_y, "SPINE MRI RADIOLOGY REPORT (Continued)")
                current_y -= 10
                c.line(left_margin, current_y, width - right_margin, current_y)
                current_y -= 30

            c.drawImage(ImageReader(img_io),
                        image_x,
                        current_y - img_height - 10,  
                        width=img_width,
                        height=img_height)

            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(width / 2, current_y - img_height - 25, "Figure 1: MRI of lumbar spine (Source: Patient Upload)")
            current_y -= (img_height + 40)  
            
        except Exception as e:
            print(f"Error embedding image in PDF for report {report.id}: {e}") 
            c.setFont("Helvetica-Italic", 10)
            c.drawString(left_margin, current_y - 20, "Note: Image could not be loaded for this report.")
            current_y -= 30

    # Footer 
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(left_margin, 30, "This report was generated by MedBot AI Radiology Assistant")
    c.drawString(width - right_margin - 150, 30, datetime.now().strftime("%Y-%m-%d %H:%M"))

    c.save()
    buffer.seek(0)

    # Email with PDF attachment 
    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = req.email_to
    msg["Subject"] = f"Spine MRI Report for {report.patient_name}"
    msg.attach(MIMEText(f"Dear Doctor,\n\nPlease find attached the MRI report for {report.patient_name}.\n\nRegards,\nMedBot AI", "plain"))

    attachment = MIMEApplication(buffer.read(), Name=f"Spine_MRI_Report_{report.patient_name.replace(' ', '_')}_{report.exam_date}.pdf")
    attachment["Content-Disposition"] = f'attachment; filename="Spine_MRI_Report_{report.patient_name.replace(" ", "_")}_{report.exam_date}.pdf"'
    msg.attach(attachment)

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send email: {str(e)}. Check SMTP settings.")

    return {"msg": f"Report sent to {req.email_to}"}

@app.post("/report/export")
def export_report(req: ExportRequest, current_user=Depends(get_current_user)): 
    return {
        "msg": f"Report {req.report_id} export requested as {req.format}",
        "download_url": f"/exports/{req.report_id}.{req.format}"  
    }

@app.put("/user/update")
def update_user(update_data: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = crud.get_user_by_username(db, current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    updates = {}
    if update_data.email:
        updates["email"] = update_data.email
    if update_data.password:
        updates["hashed_password"] = get_password_hash(update_data.password)
    
    if updates: 
        updated_user = crud.update_user_fields(db, user, updates)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")
    
    return {"msg": "User updated successfully"}

@app.post("/support")
def contact_support(request: SupportRequest): 
    print(f"Support request from {request.email}: {request.message}")  
    return {"msg": "Support request received. We'll contact you soon."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.delete("/report/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(report_id: int = Path(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    report = crud.get_report_by_id(db, report_id, current_user.username)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or not authorized to delete.")
    
    if not crud.delete_report(db, report_id, current_user.username):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete report.")
    
    return {"msg": "Report deleted successfully"}

@app.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user = crud.get_user_by_username(db, current_user.username)
    if not user or not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
    
    if req.new_password == req.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as the current password")

    user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    db.refresh(user) 
    return {"msg": "Password changed successfully"}

@app.delete("/delete-account", status_code=status.HTTP_200_OK)
def delete_account(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user = crud.get_user_by_username(db, current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
     
    crud.delete_all_reports_by_user(db, current_user.username)  
    
    if not crud.delete_user(db, current_user.username):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete account.")
    
    return {"msg": "Account deleted successfully"}