# DWC Omnichat â€” Implementation & Testing Guide

This guide assumes **no prior experience**. Follow each step, test as you go, and youâ€™ll catch mistakes early.

---

## 0) Install What You Need (Once)

- **Python 3.10+** (Windows Store or python.org)  
  [Screenshot: Windows 'Apps & Features' showing Python installed]
- **PowerShell** (Windows 10/11 built-in)  
- **Twilio account** (for SMS/WhatsApp): https://www.twilio.com/
- **Facebook Developer account** (for Messenger): https://developers.facebook.com/  *(Optional)*
- **WordPress admin access** (to embed the web chat widget) *(Optional)*
- **Render.com account** (for cloud deploy) *(Optional)*

---

## 1) Create the Project (Automatic)

Open PowerShell and run the bootstrap script (you already did if you see this file).

It created a folder on your Desktop:  
DWC-Omnichat/ with everything inside.

---

## 2) Prepare Your Environment

### 2.1 Create a virtual environment and install packages

In PowerShell:

`powershell
cd "C:\Users\bluel\Desktop\DWC-Omnichat"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
