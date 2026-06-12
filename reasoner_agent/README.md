# VakilAgent – Reasoner Agent

A production‑ready FastAPI service that receives **Watcher** events, analyses case history, runs safety checks, updates risk scores, optionally calls **Groq**, builds an **action package**, and routes it to downstream agents.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Service](#running-the-service)
- [API Endpoints](#api-endpoints)
- [Testing Commands](#testing-commands)
- [Logging](#logging)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Features
- Continuous Redis listener on `reasoner_tasks`
- Full case‑history pull from PostgreSQL
- 5 rule‑based safety checks (never downgrade urgency)
- Dynamic risk‑score calculation (ccapped at 100)
- Groq LLaMA‑3 contextual refinement with retries
- Immediate escalation for critical events
- Action package creation & routing to appropriate agents
- Lawyer‑override endpoint with audit tagging
- JSON‑structured logging to `supervisor_logs` channel
- Health, status, and risk‑score endpoints

## Installation
```bash
# Clone the repository (already present under e:\VakilAI\drafter_agent)
cd e:\VakilAI\drafter_agent

# Create a virtual environment (optional but recommended)
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r reasoner_agent/requirements.txt
