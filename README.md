# 🏛️ SVSU Intelligent

**Official AI Chatbot for Shri Vishwakarma Skill University**

Built with LangChain, Groq (Llama 3.1), and Streamlit. Answers questions about admissions, courses, faculty, and all university information by crawling 300+ pages of the official SVSU website.

---

## ✨ Features

- 🔍 **Deep Knowledge:** 300+ pages crawled from `svsu.ac.in`
- ⚡ **Ultra-Fast Responses:** Powered by Groq (Llama 3.1 8B Instant)
- 🔗 **Source Links:** Provides official website links with every answer
- 🤖 **Smart Retrieval:** Hybrid BM25 + FAISS vector search
- 🏛️ **Official UI:** Premium design matching SVSU's branding

---

## 🚀 Setup & Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/svsu-intelligent.git
cd svsu-intelligent
```

### 2. Create a Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Your API Keys
Create a `.env` file in the root directory:
```
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Build the Knowledge Base
```bash
python ingest.py
```
> This will crawl svsu.ac.in and build the FAISS + BM25 database (~10-15 min).

### 6. Run the Chatbot
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **LLM** | Groq (Llama 3.1 8B Instant) |
| **Embeddings** | HuggingFace (all-MiniLM-L6-v2) |
| **Vector DB** | FAISS |
| **Keyword Search**| BM25 (Ensemble) |
| **Framework** | LangChain |
| **UI** | Streamlit |
| **Data Source** | svsu.ac.in (300+ pages) |

---

## ☁️ Deploy to Azure VM

See [Azure VM Hosting Guide](azure_vm_hosting_plan.md) for full deployment steps.

---

*Made for Shri Vishwakarma Skill University, Haryana* 🎓
