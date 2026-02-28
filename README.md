# DeFi Transaction Failure Diagnosis AI Agent

A complete DeFi Transaction Failure Diagnosis AI Agent with a hybrid architecture combining rule-based checks and an LLM explanation engine. Built on Streamlit, it supports Ethereum, Polygon, Arbitrum, and BSC.

## Features
- **Multi-Chain Support**: Connects to Ethereum, Polygon, Arbitrum, and BSC via Web3.py.
- **RPC Fallback Mechanism**: Robust handling of RPC endpoints with automatic fallbacks for reliability.
- **Safety Layer**: Verifies transaction finality and timestamp freshness to prevent hallucinations.
- **Rule-Based Error Classifier**: Categorizes errors into Revert, Gas, Execution, and Structural issues.
- **LLM Explanation Engine**: Uses LangChain and OpenAI to provide structured responses (WHAT | WHY | HOW | CONFIDENCE).
- **Uniswap Integration**: Specific analysis capabilities for swap failures.

## Setup Instructions

1. **Clone the repository** (if not already done).

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your `OPENAI_API_KEY` and any specific RPC URLs for Alchemy/Infura if you want better reliability than public endpoints.

4. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

## Usage
- Open the application in your browser (usually http://localhost:8501).
- Select a network from the dropdown.
- Select an example transaction or paste a transaction hash you want to analyze.
- View the structured AI explanation, technical details, safety checks, and suggested fixes across the different tabs.
