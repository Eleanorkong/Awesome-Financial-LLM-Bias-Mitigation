# Automatic Bias Detection Dashboard

An automated tool that evaluates financial LLM research papers against the **Structural Validity Framework** -- a systematic checklist for detecting methodological biases in financial AI evaluations.

Based on the paper: *"Evaluating LLMs in Finance Requires Explicit Bias Consideration"* ([Interactive Checklist](https://eleanorkong.github.io/Awesome-Financial-LLM-Bias-Mitigation/checklist.html))

## Quick Access

To run the dashboard locally on your machine:

```bash
git clone https://github.com/Eleanorkong/Awesome-Financial-LLM-Bias-Mitigation.git
cd Awesome-Financial-LLM-Bias-Mitigation/automatic_bias_detection_dashboard
python3 -m venv venv
source venv/bin/activate
pip install -e .
python run.py
```

Then open **[http://localhost:8000](http://localhost:8000)** in your browser. The dashboard runs entirely on your machine -- your API keys and uploaded papers are never sent to any third-party server (only to the LLM provider you select).

> **Note:** This is a full-stack application (Python backend + browser frontend). It requires Python 3.11+ and must be run locally -- it cannot be hosted on static platforms like GitHub Pages.

## Getting Started

### Prerequisites

- Python 3.11+
- An API key from one of the supported LLM providers (or Ollama for local models)

### Installation

```bash
# Clone the repository
git clone https://github.com/Eleanorkong/Awesome-Financial-LLM-Bias-Mitigation.git
cd Awesome-Financial-LLM-Bias-Mitigation/automatic_bias_detection_dashboard

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Running the Dashboard

```bash
python run.py
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser.

You can optionally set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-key-here"   # For Claude models
export OPENAI_API_KEY="your-key-here"      # For OpenAI models
export GEMINI_API_KEY="your-key-here"      # For Google models
```

## How to Use

1. **Select a provider and model** from the dropdowns (or enter a custom model ID)
2. **Enter your API key** (not needed for Ollama local models)
3. **Upload a PDF** of a financial LLM research paper
4. *(Optional)* Paste a **GitHub repo URL** -- the tool will also analyze the source code
5. Click **Analyze Paper** and wait for the results

The tool makes 2 LLM API calls per paper: one to classify the paper type, and one to evaluate all 12 checklist items.

## Supported LLM Providers


| Provider      | Example Models                         | API Key Source                                            |
| ------------- | -------------------------------------- | --------------------------------------------------------- |
| **Anthropic** | Claude Sonnet 4.6, Opus 4.6, Haiku 4.5 | [console.anthropic.com](https://console.anthropic.com)    |
| **OpenAI**    | GPT-5.4, GPT-4.1, o4-mini              | [platform.openai.com](https://platform.openai.com)        |
| **Google**    | Gemini 2.5 Pro, Gemini 2.5 Flash       | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Ollama**    | Qwen3, DeepSeek-R1, Llama 3.3          | No key needed (runs locally)                              |


You can also enter any custom model ID supported by [LiteLLM](https://docs.litellm.ai/docs/providers).

## What It Checks

The dashboard evaluates papers against **12 checklist items** across **5 bias categories**:


| Section                          | Bias Type         | Checklist Items                                                                      |
| -------------------------------- | ----------------- | ------------------------------------------------------------------------------------ |
| 1. Temporal Sanitation           | Look-Ahead Bias   | 1.1 Knowledge Cutoff Disclosure, 1.2 Point-in-Time Retrieval, 1.3 Full Trace Logging |
| 2. Dynamic Universe Construction | Survivorship Bias | 2.1 Time-Indexed Universe, 2.2 Unbiased Task Sampling, 2.3 Failure Regime Reporting  |
| 3. Rationale Robustness          | Narrative Bias    | 3.1 Evidence Grounding & Auditing, 3.2 Negative Controls & Entity Substitution       |
| 4. Epistemic Calibration         | Objective Bias    | 4.1 Explicit Abstention Option, 4.2 Calibrated Confidence                            |
| 5. Realistic Implementation      | Cost Bias         | 5.1 Latency-Aware Execution, 5.2 Net Utility Reporting                               |


Each item receives a verdict of **Pass**, **Fail**, or **N/A** with:

- A detailed explanation of what was found (or not found)
- Evidence quotes from the paper and/or code
- Actionable recommendations for items that fail

Items that don't apply to a paper's methodology (e.g., trading cost checks for a QA paper) are automatically marked as N/A.

## Features

- **PDF analysis** -- upload any financial LLM research paper
- **Code analysis** -- optionally provide a GitHub repo URL to cross-reference paper claims against implementation
- **Multi-provider support** -- works with Claude, GPT, Gemini, and local Ollama models
- **Streaming progress** -- real-time progress updates during analysis
- **Local caching** -- results are saved in your browser and persist across sessions
- **Export options** -- download results as PDF, JSON, or plain text
- **Cross-check detection** -- identifies interactions between different bias types

## How It Works

```
PDF Upload → Extract Text → Classify Paper Type → Evaluate 12 Checklist Items → Generate Report
                             (LLM Call #1)         (LLM Call #2)
```

## Project Structure

```
automatic_bias_detection_dashboard/
├── app.py                          # FastAPI server
├── run.py                          # Entry point
├── pyproject.toml                  # Dependencies
├── static/
│   └── index.html                  # Frontend (single file, no build step)
└── core/
    ├── schemas.py                  # Pydantic data models
    ├── pdf_extractor.py            # PDF text extraction (PyMuPDF)
    ├── llm_client.py               # Multi-provider LLM wrapper (LiteLLM + Instructor)
    ├── paper_classifier.py         # Paper type classification
    ├── checklist_evaluator.py      # 12-item checklist evaluation
    ├── code_extractor.py           # GitHub repo code extraction
    ├── report_generator.py         # Report assembly
    └── prompts/
        ├── classification_prompt.py  # Paper classification prompt
        └── checklist_prompt.py       # Checklist evaluation prompt
```

## License

This project accompanies the research paper *"Evaluating LLMs in Finance Requires Explicit Bias Consideration"*.