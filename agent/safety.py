import time
from web3 import Web3
from .data import get_rpc_urls

FINALITY_THRESHOLDS = {
    "Ethereum": 64,
    "Polygon": 128,
    "Arbitrum": 64,
    "BSC": 15
}

def verify_consensus(network: str, tx_hash: str) -> dict:
    """
    Queries multiple RPC endpoints to ensure consensus on the transaction receipt status.
    Returns a dictionary with consensus results and any flags.
    """
    urls = get_rpc_urls(network)
    if not urls:
        return {"consensus_reached": False, "confidence": "Low", "flags": ["No RPC URLs found for consensus"]}
        
    results = []
    for url in urls[:3]:  # Check up to 3 RPCs
        try:
            from web3.middleware import ExtraDataToPOAMiddleware
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 5}))
            if network in ["Polygon", "BSC"]:
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                
            if w3.is_connected():
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                results.append(receipt.get('status'))
        except Exception:
            results.append(None)
            
    # Filter out Nones
    valid_results = [r for r in results if r is not None]
    
    if not valid_results:
        return {"consensus_reached": False, "confidence": "Low", "flags": ["Failed to fetch receipt from any RPC"]}
        
    all_same = len(set(valid_results)) == 1
    
    return {
        "consensus_reached": all_same,
        "confidence": "High" if all_same and len(valid_results) > 1 else "Medium",
        "agreed_status": valid_results[0] if all_same else None,
        "flags": [] if all_same else ["Conflicting receipt statuses across RPCs"]
    }

def check_finality(network: str, w3: Web3, receipt: dict) -> dict:
    """
    Checks if the transaction is final based on block confirmations.
    """
    if not receipt or 'blockNumber' not in receipt:
        return {"is_final": False, "confirmations": 0, "flags": ["No block number in receipt"]}
        
    try:
        current_block = w3.eth.block_number
        tx_block = receipt['blockNumber']
        confirmations = current_block - tx_block
        threshold = FINALITY_THRESHOLDS.get(network, 64)
        
        is_final = confirmations >= threshold
        
        flags = []
        if not is_final:
            flags.append(f"Transaction not final. {confirmations}/{threshold} confirmations.")
            
        return {
            "is_final": is_final,
            "confirmations": confirmations,
            "flags": flags
        }
    except Exception as e:
         return {"is_final": False, "confirmations": 0, "flags": [f"Finality check error: {str(e)}"]}

def verify_timestamp_freshness(w3: Web3, receipt: dict) -> dict:
    """
    Verifies that the block timestamp isn't wildly out of sync.
    """
    try:
         tx_block = w3.eth.get_block(receipt['blockNumber'])
         tx_time = tx_block['timestamp']
         current_time = int(time.time())
         
         # If transaction is older than say, 30 days, we just note it.
         # But the real freshness check is if the node's latest block time is close to current time.
         latest_block = w3.eth.get_block('latest')
         node_time = latest_block['timestamp']
         
         is_fresh = abs(current_time - node_time) < 3600 # Node within 1 hour of real time
         
         flags = []
         if not is_fresh:
             flags.append("Warning: RPC node seems out of sync with current time.")
             
         return {
             "node_synced": is_fresh,
             "tx_timestamp": tx_time,
             "flags": flags
         }
    except Exception as e:
         return {"node_synced": False, "tx_timestamp": 0, "flags": [f"Timestamp check error: {str(e)}"]}

def run_safety_checks(network: str, w3: Web3, receipt: dict, tx_hash: str) -> dict:
    """Runs all safety checks and aggregates results."""
    consensus = verify_consensus(network, tx_hash)
    finality = check_finality(network, w3, receipt)
    freshness = verify_timestamp_freshness(w3, receipt)
    
    all_flags = consensus['flags'] + finality['flags'] + freshness['flags']
    
    return {
        "is_safe": len(all_flags) == 0,
        "consensus": consensus,
        "finality": finality,
        "freshness": freshness,
        "all_flags": all_flags,
        "confidence": consensus['confidence'] if len(all_flags) == 0 else "Low"
    }
