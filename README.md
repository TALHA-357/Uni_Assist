# UniAssist - All-in-One University Student Hub & RAG Chatbot

**UniAssist** is a modern, production-ready SaaS web application designed for university students. It integrates a **Retrieval-Augmented Generation (RAG) Chatbot** for answering academic queries using official university regulations, alongside a highly precise **GPA/CGPA Calculator** fully compliant with **The University of Haripur (UoH) Absolute Grading System**.

The project features a **Next.js (React) Frontend** styled with a custom light-sage and navy glassmorphic theme, and a **Flask (Python) Backend** with local SQLite vector indexing.
<img width="1851" height="915" alt="Screenshot 2026-06-23 113734" src="https://github.com/user-attachments/assets/0cff8f3c-9ff6-438d-8e3a-2597affd8ed6" />

---

## ✨ Features

### 1. 🤖 RAG-Based Guideline Chatbot
* **Document Ingestion**: Upload academic handbooks, curriculum syllabi, or exam regulations in **PDF** or **TXT** format.
* **Text Chunking & Embeddings**: Automatically splits text recursively and computes high-quality vector representations using OpenAI's `text-embedding-3-small` API.
* **SQLite Vector Store**: Stores text chunks and embeddings serialized as JSON directly inside SQLite, keeping the database completely self-contained.
* **NumPy Cosine Similarity**: Employs fast matrix operations in Python to perform semantic similarity lookups on queries in milliseconds.
* **Smart Fallback Generation**: Prompts the LLM (defaulting to `gpt-4o-mini`) to synthesize replies with **document citations**. Includes auto-fallback support for reasoning models (`o1`/`o3-mini`) by dynamically replacing deprecated API parameters (`temperature` and `max_tokens`).
<img width="1852" height="911" alt="Screenshot 2026-06-23 113821" src="https://github.com/user-attachments/assets/d06e6100-f1de-4c39-b9dd-f56d0c32e124" />

### 2. 🧮 UoH GPA/CGPA Calculator
* **Percentage-Based Logic**: Fully aligns with the **University of Haripur absolute grading guidelines (Revised - 2023)**. Students input raw marks (0–100) instead of guessing letter grades.
* **Numerical Grade (NG) Mapping**: Dynamically translates percentage scores into UoH Letter Grades and decimal Numerical Grades (e.g., 50% = 1.00 D, 68% = 2.50 B-, 85%+ = 4.00 A).
* **Double-Digit Precision**: Computes term GPA and cumulative CGPA up to two decimal points, obeying the rounding regulations of the Academic Syndicate.
* **SaaS Persistence**: Authenticated users can save, load, and delete semester session lists to track their overall GPA progress.
<img width="1854" height="913" alt="Screenshot 2026-06-23 113759" src="https://github.com/user-attachments/assets/b9d3c19a-64f9-48ce-a1f9-2a2f414a420e" />

### 3. 🎨 High-Fidelity UI Design
* **University-Themed Aesthetic**: Cohesive color palette featuring light sage-green backgrounds, clean white dashboard cards, and forest-green banner headers inspired by official university portals.
* **Sidebar Navigation**: Seamless dashboard view transitions using responsive sidebar tabs.
* **Top Bar Header**: Horizontal utility header showing active user session context and registration tools.

---

## 🛠️ Architecture & Tech Stack

```
                                      +--------------------------+
                                      |    Next.js Frontend      |
                                      |     (React / TS)         |
                                      +------------+-------------+
                                                   |  API calls (JWT)
                                                   v
                                      +--------------------------+
                                      |      Flask Backend       |
                                      +------------+-------------+
                                                   |
                             +---------------------+---------------------+
                             |                                           |
                             v                                           v
               +-------------+-------------+               +-------------+-------------+
               |     Relational Database   |               |     RAG Core Service      |
               |  SQLite (SQLAlchemy ORM)  |               |    - PDF/TXT Ingestor     |
               |                           |               |    - OpenAI Embeddings    |
               | - User Profiles           |               |    - Cosine Similarity    |
               | - Saved Semester GPA      |               |    - LLM Synthesizer      |
               | - Course Details Logs     |               |                           |
               +---------------------------+               +---------------------------+
```

* **Frontend**: Next.js 15, React 19, TypeScript, Vanilla CSS (custom glassmorphism parameters & keyframes), Lucide React.
* **Backend**: Flask 3, Flask-SQLAlchemy (ORM), Flask-JWT-Extended (auth tokens), Flask-CORS.
* **AI & Processing**: OpenAI SDK, NumPy (vector similarity search), PyPDF (text extraction).
* **Database**: SQLite (default developer build).

---

## 📂 Project Directory structure

```
Uni assist/
├── backend/                  # Python Flask API
│   ├── app/
│   │   ├── __init__.py       # App creation & blueprints config
│   │   ├── models.py         # SQLAlchemy Database models
│   │   ├── routes/
│   │   │   ├── auth.py       # User sign up / sign in routes
│   │   │   ├── chat.py       # RAG queries & file upload routes
│   │   │   └── gpa.py        # GPA/CGPA arithmetic routes
│   │   └── services/
│   │       └── rag.py        # Document parsing, vectors, & LLM fallback
│   ├── requirements.txt      # Backend Python dependencies
│   ├── config.py             # Flask App configuration keys
│   └── run.py                # Server entry point
├── frontend/                 # Next.js Web App
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx    # Page SEO headers and layout wrapper
│   │   │   ├── page.tsx      # Unified client-side dashboard state & panels
│   │   │   └── globals.css   # Custom CSS Variables & global styles
│   │   └── lib/
│   │       └── api.ts        # API communication library (handles JWT)
│   ├── package.json          # Node script commands & dependencies
│   └── tsconfig.json         # TypeScript configurations
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
* **Python** (version 3.10 or higher)
* **Node.js** (version 18 or higher)
* **npm** (comes with Node.js)
* **OpenAI API Key**

---

### 1. Setup the Backend
1. Navigate into the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv myenv
   # On Windows:
   myenv\Scripts\activate
   # On macOS/Linux:
   source myenv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment credentials. Create a `.env` file inside the `backend` folder:
   ```env
   SECRET_KEY=your_flask_secret_key
   JWT_SECRET_KEY=your_jwt_secret_key
   OPENAI_API_KEY=sk-proj-yourActualOpenaiKey
   OPENAI_MODEL=gpt-4o-mini
   PORT=5000
   ```
5. Start the backend:
   ```bash
   python run.py
   ```
   *The server will start on `http://127.0.0.1:5000`. It will auto-create the database `backend/app/uniassist.db` and files upload folder `backend/uploads/` on launch.*

---

### 2. Setup the Frontend
1. Open a new terminal window and navigate into the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the Next.js development server:
   ```bash
   npm run dev
   ```
   *The client application will launch at `http://localhost:3000`.*

---

## 📈 UoH Absolute Grading Reference Chart

The GPA calculator automatically implements this conversion matrix defined by UoH regulations:

| Marks Range | Numerical Grade (NG) | Letter Grade | Quality of Performance |
| :--- | :---: | :---: | :--- |
| **85 - 100** | 4.00 | A | Excellent |
| **80 - 84** | 3.50 - 3.90 | A- | Excellent |
| **75 - 79** | 3.08 - 3.42 | B+ | Good |
| **71 - 74** | 2.75 - 3.00 | B | Good |
| **68 - 70** | 2.50 - 2.67 | B- | Good |
| **64 - 67** | 2.17 - 2.42 | C+ | Adequate |
| **61 - 63** | 1.92 - 2.08 | C | Adequate |
| **58 - 60** | 1.67 - 1.83 | C- | Adequate |
| **54 - 57** | 1.33 - 1.58 | D+ | Minimum acceptable |
| **50 - 53** | 1.00 - 1.25 | D | Minimum acceptable |
| **0 - 49** | 0.00 | F | Fail |

---

## 🛡️ Production Roadmap

To scale this project to an enterprise SaaS system, configure the following adjustments:
* **Relational Database**: Swap the local SQLite file for a managed **PostgreSQL** instance (AWS RDS, Neon, or Supabase).
* **Vector Store**: Transition the local NumPy similarity script into **pgvector** or a cloud vector database (like **Pinecone** or **Qdrant**).
* **Asynchronous Ingestion**: Ingest documents using a worker queue (such as **Celery** with **Redis**) to prevent requests from hanging when uploading heavy PDFs.
* **HTTP-Only Cookies**: Move JWT storage from `localStorage` into secure HTTP-only cookies to mitigate XSS vulnerabilities.
* **Sub-domain Multi-Tenancy**: Tag document index schemas with a `tenant_id` column to isolate handbook results by university department or campus.
