import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

class ExplanationOutput(BaseModel):
    what: str = Field(description="A brief description of what happened in the transaction.")
    why: str = Field(description="The underlying technical reason for the failure.")
    how: str = Field(description="How the user can fix the issue.")
    confidence: str = Field(description="Confidence level of this explanation (High, Medium, Low).")
    citations: list[str] = Field(description="List of data sources or rules used (e.g., 'Web3 Receipt', 'INTENT-TX-18K Rule 3').")

# Fallback template
def get_fallback_explanation(classifier_result: dict, safety_result: dict) -> ExplanationOutput:
    category = classifier_result.get("category", "Unknown")
    reason = classifier_result.get("reason", "No specific reason determined.")
    confidence = safety_result.get("confidence", "Low")
    
    return ExplanationOutput(
        what=f"The transaction failed with a {category} error.",
        why=reason,
        how="Please check your transaction parameters, gas limits, and ensure you have sufficient funds/allowance.",
        confidence=confidence,
        citations=["Rule-Based Classifier Fallback"]
    )

prompt_template = """
You are a Decentralized Finance (DeFi) Expert AI Agent specializing in interpreting Ethereum Virtual Machine (EVM) transaction failures.
Based on the provided transaction data, receipt data, rule-based classification, safety checks, and known protocol patterns, provide a structured explanation of why the transaction failed.

IMPORTANT: If the safety checks flag the data as uncertain (Confidence = Low), DO NOT make absolute claims. Use phrases like "It is likely that...", "Data suggests...", etc.

--- DATA INPUTS ---
Transaction Hash: {tx_hash}
Network: {network}
Rule-Based Classification: {classifier_category}
Classifier Reason: {classifier_reason}
Uniswap Pattern Analysis: {uniswap_analysis}
Safety Confidence: {safety_confidence}
Safety Flags: {safety_flags}

--- INSTRUCTIONS ---
Formulate your response strictly using the provided structured format.
WHAT: Simply state what the transaction tried to do and that it failed.
WHY: Explain the technical reason using the classification and Uniswap traces.
HOW: Give the user actionable steps to fix or retry the transaction.
CONFIDENCE: Reflect the Safety Confidence provided above. Do not claim High confidence if Safety Confidence is Low/Medium or if safety flags exist.
CITATIONS: List what information sources guided your reasoning.
"""

def generate_explanation(tx_hash: str, network: str, classifier_result: dict, uniswap_result: dict, safety_result: dict) -> ExplanationOutput:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        # Missing API Key, return fallback
        return get_fallback_explanation(classifier_result, safety_result)
        
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1) # Or gpt-3.5-turbo depending on what's available
        structured_llm = llm.with_structured_output(ExplanationOutput)
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=[
                "tx_hash", "network", "classifier_category", "classifier_reason",
                "uniswap_analysis", "safety_confidence", "safety_flags"
            ]
        )
        
        chain = prompt | structured_llm
        
        result = chain.invoke({
            "tx_hash": tx_hash,
            "network": network,
            "classifier_category": classifier_result.get("category", "Unknown"),
            "classifier_reason": classifier_result.get("reason", ""),
            "uniswap_analysis": uniswap_result.get("analysis", "None"),
            "safety_confidence": safety_result.get("confidence", "Low"),
            "safety_flags": ", ".join(safety_result.get("all_flags", [])) or "None"
        })
        
        return result
        
    except Exception as e:
        print(f"LLM Error: {e}")
        return get_fallback_explanation(classifier_result, safety_result)
