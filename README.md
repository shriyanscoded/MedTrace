# BillSanjivani 🛡️
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Gemini AI](https://img.shields.io/badge/Google-Gemini%202.0%20Vision-orange.svg)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70b-red.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

**AI-Powered Indian Hospital Bill Fraud Detector**

## 🚨 The Problem (with real stats)
- India loses ₹8,000-10,000 crore annually to hospital fraud
- Patients are overcharged for medicines, tests, and consumables
- Common people have no way to verify if their bill is fair
- No existing tool audits Indian hospital bills with AI

## ✨ Features
- 📸 **Upload any hospital bill photo (JPG/PNG)**
- 🤖 **Gemini 2.0 Vision reads every line item automatically**
- 🔍 **Searches real Indian market prices via Serper API**
- ⚖️ **Groq AI detects fraud with confidence scores**
- 📊 **Shows fair price RANGES (not just one price)**
- 📍 **Location-specific pricing (Mumbai vs Rural UP vs Chennai)**
- 💬 **AI Chat Assistant to answer bill questions**
- 🌍 **Understands Hindi and regional language questions**
- 🖨️ **Print/Download fraud report**

## 🛠️ Tech Stack
| Layer | Technology |
|---|---|
| Frontend | Pure HTML + CSS + Vanilla JS |
| Backend | Python FastAPI |
| Vision AI | Google Gemini 2.0 Flash |
| Price Research | Serper API |
| Fraud Analysis | Groq llama-3.3-70b-versatile |

## 🤖 Agentic AI Pipeline
📸 **Bill Photo Upload**
↓
🤖 **Agent 1:** Gemini Vision reads and extracts all items
↓
🔍 **Agent 2:** Serper searches market prices for each item
↓
⚖️ **Agent 3:** Groq analyzes fraud and generates report
↓
💬 **Agent 4:** AI Chat Assistant answers follow-up questions

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser

### Step 1: Clone
```bash
git clone https://github.com/yourusername/billsanjivani
cd billsanjivani
```

### Step 2: Get FREE API Keys
| API | Link | Free Tier |
|---|---|---|
| Gemini | [aistudio.google.com](https://aistudio.google.com) | Very generous free tier |
| Serper | [serper.dev](https://serper.dev) | 2,500 free searches |
| Groq | [console.groq.com](https://console.groq.com) | Completely free |

### Step 3: Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env file
```

### Step 4: Run Backend
```bash
python -m uvicorn main:app --reload --port 8000
```

### Step 5: Open Frontend
Open `frontend/index.html` in your browser.
That's it! No npm, no Node.js needed.

## 📱 How To Use
1. Open `index.html` in browser
2. Upload a photo of your hospital bill
3. Click "Analyze Bill"
4. Wait 15-20 seconds for AI analysis
5. View fraud report with overcharge details
6. Chat with AI about your bill
7. Ask location-specific prices
8. Print/save the report

## 🎯 What Makes It Different
- First AI tool specifically for Indian hospital bill fraud
- Shows price RANGES not single prices (more accurate)
- Location-aware pricing (rural vs metro)
- Conversational AI assistant for follow-up questions
- No login required, works offline after setup
- Completely free to use

## 📊 Example Results
**Total Billed:** ₹24,650
**Fair Price Range:** ₹2,100 - ₹5,800
**Potential Overcharge:** ₹18,850 - ₹22,550
**Flagged Items:** 8 out of 10

## 🏆 Built For
Hack & Break: Generative AI & Cybersecurity Innovation Challenge - IIT Bombay 2026
Theme: Agentic AI

## ⚠️ Disclaimer
BillSanjivani provides AI-estimated price ranges for reference only. Always consult a medical billing expert or consumer court for legal disputes. Prices vary by location, hospital type, and time.

## 📄 License
MIT License - Free to use and modify

## 🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first.
