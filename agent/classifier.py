import json

def classify_error(tx: dict, receipt: dict, trace: dict = None, w3=None) -> dict:
    """
    Categorizes the transaction failure into Revert, Gas, Execution, or Structural issues.
    Based on INTENT-TX-18K taxonomy.
    """
    if receipt is None:
        return {"category": "Unknown", "reason": "Receipt not found"}
        
    if receipt.get("status") == 1:
        return {"category": "Success", "reason": "Transaction is successful"}
        
    category = "Revert" # Default
    detailed_reason = "Transaction reverted without a specific reason available."
    
    # 1. Gas Issues
    gas_limit = tx.get("gas", 0)
    gas_used = receipt.get("gasUsed", 0)
    
    if gas_used >= gas_limit:
        category = "Gas Issue"
        detailed_reason = f"Out of Gas error. Transaction used all gas limit ({gas_used} / {gas_limit})."
        return {"category": category, "reason": detailed_reason}
        
    # 2. Execution / Structural check via `eth_call` (Simulate to get revert reason)
    if w3 and tx.get("to") and category == "Revert":
        try:
            # We must set block_identifier to the block before it was mined if we want the accurate error,
            # but standard networks might not keep archive state.
            # Attempting an eth_call on 'latest' for the exact same tx parameters often yields the revert reason
            # if the state hasn't changed dramatically to cause a different error.
            call_tx = {
                "to": tx["to"],
                "data": tx.get("input", "0x"),
                "value": tx.get("value", 0),
                "from": tx["from"]
            }
            w3.eth.call(call_tx)
        except Exception as e:
            err_msg = str(e)
            detailed_reason = f"Revert Reason: {err_msg}"
            
            # Simple heuristic classification based on string matching
            if "insufficient funds" in err_msg.lower() or "balance" in err_msg.lower():
                category = "Execution Issue"
            elif "transfer amount exceeds allowance" in err_msg.lower():
                category = "Execution Issue"
            elif "expired" in err_msg.lower() or "deadline" in err_msg.lower() or "slippage" in err_msg.lower() or "amount" in err_msg.lower():
                category = "Structural Issue" # E.g., AMM parameters
            else:
                category = "Revert"

    # 3. Check Traces if available
    if trace and isinstance(trace, dict) and "returnValue" in trace:
        # If we had a trace, we could decode the return value to ABI string
        # This is a simplification.
        if "Execution reverted" in str(trace):
            pass

    return {
        "category": category,
        "reason": detailed_reason
    }
