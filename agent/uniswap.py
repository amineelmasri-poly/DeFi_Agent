def analyze_uniswap_swap(tx: dict, receipt: dict, classifier_result: dict) -> dict:
    """
    Specifically analyzes failing swap transactions for DEX protocols (like Uniswap).
    Uses Viem-integration / Swap-integration patterns translated to Python.
    """
    if classifier_result["category"] != "Structural Issue" and classifier_result["category"] != "Revert":
        return {"is_swap_related": False, "analysis": None}
        
    reason = classifier_result["reason"].lower()
    
    is_swap = False
    analysis = "No specific swap patterns detected."
    
    # Simple heuristics based on common DEX router revert reasons or signatures
    # (e.g. 0x5c11d795 corresponds to exactInputSingle, etc.)
    tx_input = tx.get("input", "").lower()
    
    if "uniswap" in reason or "pancakeswap" in reason or "sushiswap" in reason:
        is_swap = True
        
    # Uniswap V2 Router common signatures:
    # swapExactTokensForTokens: 0x38ed1739
    # swapExactETHForTokens: 0x7ff36ab5
    if tx_input.startswith("0x38ed1739") or tx_input.startswith("0x7ff36ab5") or "0x5c11d795" in tx_input:
        is_swap = True
        
    if is_swap:
        if "deadline" in reason or "expired" in reason:
            analysis = "Transaction expired. The swap was not executed before the specified deadline. Increase the deadline value in the router call."
        elif "amount" in reason or "output amount" in reason or "slippage" in reason:
            analysis = "Slippage tolerance exceeded. The transaction output amount was less than the minimum required (amountOutMinimum). Try increasing your slippage tolerance."
        elif "allowance" in reason or "approve" in reason:
             analysis = "Insufficient token allowance. You must approve the router contract to spend your tokens before swapping."
        else:
             analysis = "DEX swap reverted. Ensure adequate token balances, allowances, and reasonable slippage limits."
             
    return {
         "is_swap_related": is_swap,
         "analysis": analysis if is_swap else None
    }
