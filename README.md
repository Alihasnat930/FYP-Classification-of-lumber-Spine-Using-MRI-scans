

# 🧠 MedBot - Classification of lumber spine with MRI images RSNA

An intelligent web-based system for analyzing and generating diagnostic reports from **Lumbar Spine MRI scans** using the*RSNA 2024 Kaggle Dataset

# 📌 Overview

MedBot leverages deep learning to classify MRI images of the lumbar spine and generate a structured report including findings, history, technique, and visual evidence. Designed to assist radiologists, this tool can:
- Analyze uploaded MRI images
- Classify spinal conditions
- Generate downloadable PDF reports
- Email reports directly to clinicians
- Provide user authentication and account management



# 📁 Dataset

**RSNA 2024 - Lumbar Spine MRI**  
Source: [Kaggle RSNA Competition](https://www.kaggle.com/)  
- Modality: DICOM (converted to JPG/PNG for web)
- Classes:
  - Normal
  - Disc Herniation
  - Spinal Stenosis

# ✨ Features

 🖼️ Upload & Analyze MRI images
 📄 AI-generated detailed reports
 📥 PDF report download with embedded scan
 📧 Email reports directly to doctors
 🔐 User authentication (JWT + SHA-256 hashing)
 🔁 Change password & delete account options
 📊 Dashboard with recent activity

# 📊 Model Performance
# ModelName	      Architecture	                                      Settings	                             Train Accuracy ValidationAccuracy
Model A	       MVCNN (MobileNetV2)	No augmentation, 400k images, last 65 layers trainable, 80/20 split     	83.43%	        77.73%
Model B        MVCNN (MobileNetV2)	No augmentation, no early stopping, 
                                                     no LR reduction, label smoothing, 
                                                      last 65 layers trainable, 80/20 split	                  95.65%	        76.10%

# Notes:

Both models were trained on 400,000 MRI images from the RSNA 2024 dataset.

Model A showed better generalization with balanced training.

Model B, despite a higher training accuracy, experienced some overfitting due to the lack of regularization (no early stopping or learning rate adjustment).

No data augmentation was applied in either case.



# 🛠️ Tech Stack

 # Layer        # Technology               

 Frontend      Streamlit                 
 Backend API   FastAPI                   
 ML Model      PyTorch / TensorFlow (custom CNN) 
 Database      PostgreSQL (via SQLAlchemy) 
 Auth          OAuth2 + SHA-256 hashing  
 PDF Reports   ReportLab + PIL           



# 🚀 How to Run Locally

# 1. Clone the Repository

# 2. Backend (FastAPI)

cd backend
pip install -r requirements.txt
uvicorn main:app --reload


 # 3. Frontend (Streamlit)


cd frontend
pip install -r requirements.txt
streamlit run app.py



 # 🔒 Security Features

* SHA-256 password hashing
* JWT token-based authentication
* Session-based secure navigation
* Change password and delete account features

# 📄 Sample Report Output

PDF reports include:

* Patient Name, Exam Date, Created Date
* Technique & History
* AI-generated Findings
* MRI Image Snapshot
* Download or Email options

# 👤 User Interface Design

* Sidebar navigation with:

  * Dashboard
  * Upload & Analyze
  * View Reports
  * Email Reports
  * Settings (change password, delete account)
* Clean dark theme using custom Streamlit CSS
* Expander sections for report viewing
* Image preview & download buttons


# 📬 Feedback Displayed to Users

* Upload status and analysis result feedback
* Success/failure messages for login, email, and report generation
* Real-time progress with spinners and alerts


# 📧 Contact

For questions, feedback or collaboration:
📫 syedalihasant929@gmail.com

 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

