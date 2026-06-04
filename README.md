# ⚖️ VakilAgent — Agentic AI for Indian Court Workflows

> *"Provakil tells you the building is on fire. VakilAgent calls the fire brigade."*

---

## 📌 Problem Statement

India has over **5 crore pending court cases**. Small lawyers managing 40–60 cases daily are drowning — not because they lack skill, but because every court update demands a manual response: notify the client, draft a document, read an order, prepare for tomorrow.

Every court update creates **5 manual tasks** for a lawyer:
- Manually WhatsApp the client about the new date
- Manually check what documents are needed
- Manually read and summarise new orders
- Manually draft adjournment applications
- Manually update their case diary

Multiply that by 50 cases and 365 days. That is why lawyers are buried in admin work instead of practising law.

**Existing tools like Provakil notify lawyers. They stop there. Nobody acts.**

VakilAgent is the first agentic system that converts a court event directly into completed action — autonomously, intelligently, and safely.

---

## 💡 Solution

**VakilAgent** is a role-aware autonomous agent that:

1. **Watches** eCourts API 24/7 for any case updates
2. **Understands** what type of event occurred and its legal significance
3. **Acts** automatically — notifies clients, summarises orders, drafts documents
4. **Escalates** only when the lawyer's judgment is genuinely needed

The lawyer wakes up to a dashboard that says:
> *"4 things happened overnight. 3 already handled. 1 needs your approval."*

---

## 🔄 How It Works

```
eCourts API detects update (new date / order / filing)
                ↓
VakilAgent wakes up and reads the event
                ↓
Agent reasons: What type of event? What is the urgency?
               What does case history say? What action is needed?
                ↓
┌─────────────────────────────────────────────────────┐
│  New hearing date?  → WhatsApp client automatically │
│  New order passed?  → Summarise PDF in plain Tamil/ │
│                       English for lawyer            │
│  Adjournment needed?→ Draft application, send for   │
│                       lawyer's one-click approval   │
│  Opponent filed?    → Alert lawyer with summary     │
└─────────────────────────────────────────────────────┘
                ↓
Lawyer reviews dashboard — acts only where needed
```

---

## 🤖 Agent Roles

| Agent | Responsibility |
|---|---|
| **Watcher Agent** | Monitors eCourts API continuously for all tracked cases |
| **Reasoner Agent** | Reads event type, checks case history, decides action needed |
| **Communicator Agent** | Sends WhatsApp messages to clients in their language |
| **Drafter Agent** | Generates adjournment applications, preparation checklists, order summaries |
| **Escalation Agent** | Flags high-stakes decisions that require lawyer approval |

---

## 🧠 What Makes This Agentic AI

| Capability | Description |
|---|---|
| **Perceives** | Reads eCourts API events continuously |
| **Reasons** | Understands legal context of each event |
| **Acts** | Takes appropriate autonomous action |
| **Remembers** | Maintains case history across events |
| **Escalates** | Brings lawyer in only when human judgment is needed |

---

## ⚡ Approval Model (Safe by Design)

```
Low-stakes   → Agent acts automatically
               (e.g. client reminder, hearing notification)

Medium-stakes → Agent drafts, lawyer approves in 1 click
               (e.g. adjournment application, preparation note)

High-stakes  → Agent prepares everything, lawyer signs off
               (e.g. filing in court, strategic decisions)
```

The lawyer is **never bypassed** on things that matter legally. They are only removed from things that are purely administrative.

---

## 🆚 How We Differ From Existing Solutions

| Feature | eCourts App | Provakil | VakilAgent |
|---|---|---|---|
| Monitors courts | ✅ Manual check | ✅ Automatic | ✅ Automatic |
| Sends notification | ❌ | ✅ | ✅ |
| Understands event context | ❌ | ❌ | ✅ |
| Notifies client automatically | ❌ | ❌ | ✅ |
| Reads & summarises orders | ❌ | ❌ | ✅ |
| Drafts legal documents | ❌ | ❌ | ✅ |
| Multilingual (Tamil/Hindi) | ❌ | ❌ | ✅ |
| Acts while lawyer sleeps | ❌ | ❌ | ✅ |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Agent Framework** | LangGraph / AutoGen |
| **LLM Backbone** | Claude 3.5 Sonnet (Anthropic) |
| **Court Data** | eCourts API / NJDG |
| **Messaging** | WhatsApp Business API (Twilio) |
| **Multilingual** | Claude built-in language support |
| **Scheduler** | Python APScheduler |
| **Backend** | FastAPI + Python |
| **Frontend** | React + WebSockets |
| **Database** | PostgreSQL |
| **Memory & State** | Redis |

---

## 🎯 Target Users

- **Small & solo lawyers** managing 40–60 cases across multiple courts
- **Legal aid clinics** handling high volumes with limited staff
- **Litigants** who want to stay informed without calling their lawyer daily

---

## 🌍 Real World Impact

- India has **5 crore+ pending cases** — admin overload is a major bottleneck
- A lawyer spends **3+ hours daily** on tasks VakilAgent can automate
- Missed court dates cost clients cases, money, and in criminal matters — freedom
- VakilAgent gives small lawyers the **operational power of a large firm**

---

## 🚀 Hackathon MVP Scope

For the hackathon, we are demonstrating 3 core agent actions:

1. **Auto Client Notify** — New hearing detected → WhatsApp sent to client instantly
2. **Order Summariser** — New court order uploaded → Agent reads PDF → plain-language summary generated
3. **Adjournment Drafter** — Upcoming hearing flagged → Agent drafts application → lawyer approves in one click

---

## 👥 Team

**Team Name:** *(Your Team Name)*
**Track:** Agentic AI
**Hackathon:** Import Paradox — Build-Ora

---

## 📄 License

MIT License — Built for Import Paradox Hackathon 2025
