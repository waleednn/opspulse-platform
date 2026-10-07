# OpsPulse — AI-Powered Operational Analytics Platform

OpsPulse is an enterprise-grade, AI-driven logistics and supply chain intelligence platform. It seamlessly bridges natural language queries with relational SQL databases using Google's Gemini models, enforcing strict SQL security guardrails and delivering automated root-cause analysis for logistics managers.

---

## Key Features

- **Natural Language to SQL (NL2SQL):** Converts complex operational inquiries in English or Arabic directly into optimized SQLite queries.
- **Security & Execution Guardrails:** AST and pattern-based validation layer preventing SQL injection, schema modification (`DROP`, `DELETE`, `UPDATE`), and resource-heavy executions.
- **Automated Root Cause Analysis (RCA):** Synthesizes SQL execution outputs into executive-level operational reports with actionable recommendations.
- **Executive Analytics Dashboard:** Interactive KPI monitoring metrics, carrier SLA breach rates, and warehouse dispatch lag visualizations powered by Streamlit and Plotly.
- **Resilient AI Pipeline:** Built-in retry mechanism with exponential backoff to handle API rate limits and transient server load.

---

## Architecture & Workflow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Streamlit UI   │ ──> │ Gemini AI Agent  │ ──> │ Security Guardrails │
│ (Dashboard/Chat)│ <── │ (NL2SQL Engine)  │     │ (AST Validation)    │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
         ▲                                                  │
         │              ┌──────────────────┐                │ Validated
         └───────────── │ Operational Insight│ <─────────────┤ Query
                        │   Synthesizer    │  SQLite OLAP   │
                        └──────────────────┘    Database ◄──┘
```

1. **User Inquiry:** The user inputs an ad-hoc operational question via the UI or CLI.
2. **SQL Generation:** Gemini translates the prompt into dialect-specific SQLite using structured schema context.
3. **Security Guardrail:** Validates query safety (READ-ONLY restriction, table aliasing, `LIMIT` application).
4. **Data Retrieval:** Executes the query against the local OLAP SQLite engine.
5. **RCA Insights:** Gemini processes the retrieved dataset to generate a structured executive summary, bottleneck diagnosis, and next steps.

---

## Tech Stack

- **Core Framework:** Python 3.10+
- **LLM Engine:** Google GenAI SDK (`google-genai`)
- **Frontend / Dashboard:** Streamlit, Plotly
- **Data & Processing:** Pandas, SQLite
- **Environment Management:** `python-dotenv`


---

##  Quickstart Guide

### 1. Prerequisites
- Python 3.10 or higher installed.
- A Google Gemini API Key ([Get an API Key](https://aistudio.google.com/)).

### 2. Setup Environment
Clone the repository and navigate into the project directory:
```bash
cd opspulse-platform
```

Create and activate a virtual environment:
```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the example `.env` file and insert your API key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Initialize Database
Generate the schema and sample operational dataset (35,000+ records):
```bash
python src/database.py
```

### 5. Launch the Application
Run the Streamlit Dashboard:
```bash
streamlit run app/main.py
```

---

##  Sample Inquiries to Try

- **Carrier Comparison:** " قارن بين أداء شركات الشحن المختلفة في منطقة الرياض من حيث نسبة التأخير ومتوسط ساعات التأخير"
- **Hub Bottlenecks:** "ما هو متوسط وقت التجهيز في مستودع جدة مقارنة بباقي المستودعات؟"
- **Revenue at Risk:** "ما هي أكثر شرائح العملاء مساهمة في الأرباح المعرضة للخطر؟"

---

##  Guardrail Rules Implemented

- **Read-Only Constraint:** Only `SELECT` statements are permitted.
- **DDL/DML Blocking:** Strict rejection of `DROP`, `ALTER`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`.
- **Query Bounding:** Automatically injects a maximum `LIMIT 100` if no `LIMIT` is specified.
- **Syntax Integrity:** Sanitizes markdown code fences and unnecessary trailing characters.