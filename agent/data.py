import os
import time
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from dotenv import load_dotenv

load_dotenv()

# Pre-defined public endpoints as fallbacks for each network
DEFAULT_RPCS = {
    "Ethereum": [
        "https://eth.llamarpc.com",
        "https://rpc.ankr.com/eth",
        "https://cloudflare-eth.com"
    ],
    "Polygon": [
        "https://polygon-rpc.com",
        "https://rpc-mainnet.maticvigil.com",
        "https://rpc.ankr.com/polygon"
    ],
    "Arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://rpc.ankr.com/arbitrum",
        "https://arbitrum.llamarpc.com"
    ],
    "BSC": [
        "https://bsc-dataseed.binance.org/",
        "https://bsc-dataseed1.defibit.io/",
        "https://rpc.ankr.com/bsc"
    ]
}

def get_rpc_urls(network: str) -> list:
    """Gets RPC urls from environment or falls back to defaults."""
    env_key = f"{network.upper()}_RPC_URLS"
    env_urls = os.getenv(env_key)
    if env_urls:
        urls = [url.strip() for url in env_urls.split(',') if url.strip()]
        if urls:
            return urls
    return DEFAULT_RPCS.get(network, [])

class Web3ConnectionManager:
    """Manages connections to multiple RPCs with fallback support."""
    
    def __init__(self, network: str):
        self.network = network
        self.rpc_urls = get_rpc_urls(network)
        self.active_w3 = None
        self._connect()

    def _connect(self):
        """Attempts to connect to the first available RPC."""
        for url in self.rpc_urls:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if self.network in ["Polygon", "BSC"]:
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if w3.is_connected():
                self.active_w3 = w3
                return
        raise ConnectionError(f"Failed to connect to any RPC for network {self.network}")

    def get_transaction(self, tx_hash: str):
        """Fetches the transaction details."""
        if not self.active_w3:
            raise ConnectionError("No active Web3 connection.")
        try:
            return self.active_w3.eth.get_transaction(tx_hash)
        except Exception as e:
            # Simple fallback strategy: Reconnect and try again
            self._connect()
            return self.active_w3.eth.get_transaction(tx_hash)

    def get_transaction_receipt(self, tx_hash: str):
        """Fetches the transaction receipt."""
        if not self.active_w3:
            raise ConnectionError("No active Web3 connection.")
        try:
            return self.active_w3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            self._connect()
            return self.active_w3.eth.get_transaction_receipt(tx_hash)

def fetch_transaction_data(network: str, tx_hash: str):
    """Convenience function to fetch everything for a single tx."""
    manager = Web3ConnectionManager(network)
    tx = manager.get_transaction(tx_hash)
    receipt = manager.get_transaction_receipt(tx_hash)
    
    # We may try to fetch a trace if possible, but many public nodes don't support debug_traceTransaction
    # We will simulate missing traces gracefully.
    trace = None
    try:
        # Just an attempt using standard debug_traceTransaction if the node supports it
        trace = manager.active_w3.provider.make_request("debug_traceTransaction", [tx_hash, {"tracer": "callTracer"}])
        if "result" in trace:
            trace = trace["result"]
    except Exception:
        pass
        
    return {
        "transaction": dict(tx) if tx else None,
        "receipt": dict(receipt) if receipt else None,
        "trace": trace,
        "manager": manager # Return manager for further queries
    }
