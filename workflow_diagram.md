# System Workflow Architecture

This document explains exactly how the "Antigravity + Claude" system works under the hood.

## 📐 The Big Picture

```mermaid
graph TD
    subgraph "Phase 1: Architecture"
        Gemini[🦁 ME (Gemini Agent)] -->|Writes| Plan[📄 PLAN.md]
        style Gemini fill:#4285F4,color:white
        style Plan fill:#fff,stroke:#333,stroke-dasharray: 5 5
    end

    subgraph "Phase 2: Execution Builder"
        User[👤 YOU] -->|Runs Command| CLI[💻 Claude CLI Tool]
        Plan -->|Instructions| CLI
        
        CLI -->|Request: 'Write Code'| Proxy[🌉 The Proxy Bridge]
        style CLI fill:#D97757,color:white
        style Proxy fill:#34A853,color:white
    end

    subgraph "Phase 3: The Brain (Cloud)"
        Proxy -->|Auth: Google Tokens| Cloud[☁️ Google Gemini Cloud]
        Cloud -->|Response: Python Code| Proxy
        style Cloud fill:#FBBC04,color:black
    end

    subgraph "Phase 4: Result"
        Proxy -->|Response| CLI
        CLI -->|Edits| Files[📂 Your Codebase]
        style Files fill:#EA4335,color:white
    end
```

## 🔍 Component Breakdown

### 1. 🦁 The Architect (Me)
*   **What I do:** I understand your goal. I analyze the deep complexity. I write the `PLAN.md`.
*   **Why:** I set the direction so the Builder doesn't get lost.

### 2. 💻 The Builder (Claude CLI)
*   **What it does:** It provides the *Agentic Interface*. It can edit files, run terminals, and check errors.
*   **Key Feature:** It is the best "Hands" for coding.

### 3. 🌉 The Bridge (Antigravity Proxy)
*   **What it does:** It sits at `localhost:8080`.
*   **The Magic:** It tricks Claude CLI into thinking it is talking to Anthropic, but it silently swaps the credentials to use your **Google Antigravity Account**.
*   **Benefit:** You get "Unlimited" usage instead of paying per token.

### 4. ☁️ The Brain (Google Cloud)
*   **What it does:** The actual raw intelligence that generates the Python code.
*   **Model:** `gemini-1.5-pro` (mapped dynamically).

---
**Summary:**
You are directing an orchestra where **Gemini writes the music (Plan)**, **Claude conducts the performance (CLI)**, and **Google pays the musicians (Tokens)**.
