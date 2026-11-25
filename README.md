# 🛍️ SFCC Promotion AI Agent

An autonomous AI agent designed to manage Salesforce Commerce Cloud (SFCC) promotions effortlessly using natural language.

Powered by:
- **Python 3.13** backend
- **Streamlit** for real-time conversational and visual UI
- **UV** as the fast, modern package and environment manager
- **Groq LLM** (`openai/gpt-oss-120b`) for rapid agent reasoning and function calling
- **LangChain / LangGraph** for tool orchestration
- **Salesforce Commerce Cloud (SCAPI)** Pricing Promotions APIs & DWSSO OAuth 2.0

---

## 🚀 Features

- 📋 **List & Search Promotions**: Real-time listing with class and status filters.
- 🔍 **Inspect Details**: View complete JSON configurations directly from SFCC.
- ✨ **Create Promotions**: Natural language generation of standard or custom promotion rules (Product, Order, Shipping).
- 🛡️ **Safety Confirmation on Destructive Actions**: 
  - Every **Modify** or **Delete** request is staged with an **Action ID (`ACT-XXXXXX`)**.
  - Renders interactive **`[Confirm & Execute]`** and **`[Cancel]`** buttons in the UI to protect against accidental changes.
  - Also accepts conversational confirmations (e.g., *"Confirm ACT-XXXXXX"*).
- 🔄 **DWSSO OAuth Token Auto-Refresh**: In-memory caching and automatic token renewal before expiration.

---

## 🛠️ Quick Start

### 1. Prerequisites
Ensure you have `uv` installed:
```bash
brew install uv
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Set the following in `.env`:
```env
# Groq LLM API Configuration
GROQ_API_KEY=your_actual_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

# Salesforce Commerce Cloud (SFCC) Basic Auth
# Pass either raw base64 or 'Basic <base64>'
SFCC_BASIC_AUTH=Basic your_base64_auth_here

# SFCC Tenant Configuration
SFCC_SHORT_CODE=your_short_code_here
SFCC_ORG_ID=f_ecom_your_org_id_here
SFCC_SITE_ID=your_site_id_here

# SFCC Token Endpoint
SFCC_TOKEN_URL=https://account.demandware.com/dwsso/oauth2/access_token
```

### 3. Run the Streamlit Application
```bash
uv run streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Unit Tests
```bash
uv run python -m unittest discover tests
```

---

## 💬 Example Commands to Try with the AI Agent

- *"List all promotions currently active in the site."*
- *"Inspect promotion 'promo_demo_01'."*
- *"Create a 15% discount product promotion named 'Flash Weekend' with ID 'flash_weekend_15'."*
- *"Disable promotion 'promo_demo_01'."* (triggers confirmation card)
- *"Delete promotion 'promo_demo_01'."* (triggers confirmation card)
