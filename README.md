# Dynamic DMN Based Resume Analyzer

Developed as an academic group project for the Formal Languages and Automata class at Eskisehir Osmangazi University (2024-2025). A desktop application designed to automate the initial screening of resumes. This project combines regular expressions with a deterministic finite automaton (DFA), powered by the camunda 7 decision model and notation (DMN) engine, to evaluate candidate qualifications against dynamic user-defined criteria.

## Features

* **Automated Data Extraction:** Uses `PyMuPDF` and complex Regular Expressions to parse PDF resumes and extract candidate names, contact information, education history, and years of experience.
* **Dynamic Skill Matching:** Scans resume text against a user-defined list of required skills (case-insensitive, whole-word matching).
* **DFA-Driven Decision Logic:** Implements a finite state machine to navigate the evaluation process (e.g., Evaluating Minimum Experience -> Evaluating Skills -> Evaluating Preferred Experience).
* **Externalized Business Rules (DMN):** State transitions are decoupled from the Python code and evaluated externally via the Camunda 7 REST API using a DMN table. This allows business rules to be updated without altering the application code.
* **Batch Processing:** Evaluate a single resume or process an entire directory of PDF resumes simultaneously.
* **Automated Reporting:** Generates a structured text report (`resume_analysis_report.txt`) summarizing candidate details, extracted metrics, and final system decisions (Accept, Reject, or Review).
* **User-Friendly GUI:** Built with Python's `tkinter` (themed with `ttk`), providing an interface for configuring requirements and viewing real-time evaluation traces.

## Architecture & How It Works

1. **Input & Configuration:** The user selects resumes via the GUI and inputs their requirements (Minimum Experience, Preferred Experience, and a set of Required Skills).
2. **Text Parsing:** `pdf_parser.py` extracts raw text from the PDFs. `resume_analyzer.py` then applies Regex to find specific data points and calculate the candidate's metrics.
3. **State Machine Execution:** The application initializes the candidate at the `START` state. 
4. **Camunda DMN Engine:** For each state, the application calculates an `inputSymbol` (e.g., `MIN_EXP_MET`, `USER_SKILLS_PARTIAL_FOUND`) and sends an HTTP POST request to a local Camunda engine. The DMN table evaluates the state-symbol pair and returns the `nextState`.
5. **Resolution:** The loop continues until the candidate reaches a terminal state (`FINAL_ACCEPT`, `FINAL_REJECT`, or `FINAL_REVIEW`).

### DFA State Flow
* `S_START`
* `S_EVAL_MIN_EXP`
* `S_EVAL_SKILLS`
* `S_EVAL_PREF_EXP`
* **Final States:** `FINAL_ACCEPT`, `FINAL_REJECT`, `FINAL_REVIEW`

## Prerequisites

* **Python 3.8+**
* **Camunda Platform 7 (Run):** A local instance of the Camunda 7 engine is required to evaluate the DMN rules.
