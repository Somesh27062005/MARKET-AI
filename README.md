# MarketMind AI — Sales & Marketing Intelligence Platform

> **Generative AI-Powered** sales and marketing intelligence platform leveraging Groq's LLaMA 3.3 70B model for real-time campaign generation, pitch creation, lead scoring, market analysis, and business insights.

## 🚀 Features

| Feature | Description |
|---------|-------------|
| **Campaign Generator** | Create data-driven marketing campaigns with content ideas, ad copy, and platform strategies |
| **Sales Pitch Creator** | Craft personalized pitches with elevator pitches, value propositions, and objection handling |
| **Lead Scoring** | AI-powered lead qualification with BANT scoring, conversion probability, and action plans |
| **Market Analysis** | Comprehensive market intelligence with SWOT, trends, and competitive landscape |
| **Business Insights** | Strategic insights with growth opportunities, risk analysis, and 90-day action plans |

## 🛠 Tech Stack

- **Backend:** Flask (Python)
- **AI Model:** Groq API — LLaMA 3.3 70B Versatile
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Styling:** Custom dark theme with glassmorphism design system

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd resilient-pascal
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get your API key at [console.groq.com](https://console.groq.com)

### 3. Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## 📁 Project Structure

```
resilient-pascal/
├── app.py               # Flask backend with all AI routes
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── static/
│   └── style.css        # Premium dark theme design system
└── templates/
    └── index.html       # Single-page app with all features
```

## 🔑 API Configuration

| Setting | Value |
|---------|-------|
| Model | `llama-3.3-70b-versatile` |
| Host | `127.0.0.1` (localhost) |
| Port | `5000` |
| Debug Mode | `True` (development) |

## 📋 Test Cases

1. **Campaign Generation:** Product: "AI email marketing platform" → Target: "Marketing managers, e-commerce" → Platform: "LinkedIn, Instagram"
2. **Sales Pitch:** Product: "Cloud inventory management" → Customer: "Fortune 500 retail, Operations Director"
3. **Lead Scoring:** Lead: "Sarah Johnson" → Budget: "$150,000" → Need: "Customer retention" → Urgency: "High priority, Q3 deadline"
