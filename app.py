import streamlit as st
import time
import json
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Import Agent Modules
from agent.data import fetch_transaction_data
from agent.safety import run_safety_checks
from agent.classifier import classify_error
from agent.uniswap import analyze_uniswap_swap
from agent.llm import generate_explanation, ExplanationOutput
from agent.examples import EXAMPLE_TRANSACTIONS
from web3.exceptions import TransactionNotFound

# --- Setup Streamlit Page ---
st.set_page_config(page_title="DeFi Transaction Agent", page_icon="🔍", layout="wide")
st.title("DeFi Transaction Failure Diagnosis Agent 🔍")
st.markdown("Analyze failed EVM transactions using a Hybrid Rule-Based & AI approach.")

# --- State Management ---
if "history" not in st.session_state:
    st.session_state.history = []

if "current_hash" not in st.session_state:
    st.session_state.current_hash = ""
    
if "current_network" not in st.session_state:
    st.session_state.current_network = "Ethereum"

# --- Sidebar ---
with st.sidebar:
    st.header("Settings & History")
    
    st.subheader("Try an Example")
    example_options = ["Custom"] + list(EXAMPLE_TRANSACTIONS.keys())
    selected_example = st.selectbox("Select Example Transaction", options=example_options)
    
    if selected_example != "Custom":
        st.session_state.current_hash = EXAMPLE_TRANSACTIONS[selected_example]["hash"]
        st.session_state.current_network = EXAMPLE_TRANSACTIONS[selected_example]["network"]
        st.info(f"Loaded {st.session_state.current_network} example transaction.")
        
    st.divider()
    
    st.subheader("Search History")
    for item in reversed(st.session_state.history[-5:]): # Show last 5
        st.text(f"{item['network']}: {item['hash'][:8]}...")

# --- Main Layout ---
col1, col2 = st.columns([1, 2])

with col1:
    network = st.selectbox(
        "Select Network",
        options=["Ethereum", "Polygon", "Arbitrum", "BSC"],
        index=["Ethereum", "Polygon", "Arbitrum", "BSC"].index(st.session_state.current_network) if st.session_state.current_network in ["Ethereum", "Polygon", "Arbitrum", "BSC"] else 0
    )
    
    tx_hash = st.text_input("Transaction Hash", value=st.session_state.current_hash, placeholder="0x...")
    
    analyze_btn = st.button("Analyze Transaction", type="primary", use_container_width=True)

# Function to recursively convert hexbytes and similar structures to string to display safely
def json_serial(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    return str(obj)

if analyze_btn and tx_hash:
    # Save to history
    st.session_state.history.append({"network": network, "hash": tx_hash})
    
    # Run Agent
    with st.spinner(f"Analyzing transaction on {network}..."):
        # 1. Fetch Data
        try:
            st.toast("Fetching transaction data...", icon="📡")
            try:
                data_result = fetch_transaction_data(network, tx_hash)
            except TransactionNotFound:
                st.error(f"Transaction not found on {network}. Please verify the hash matches the selected network.")
                st.stop()
            except Exception as e:
                st.error(f"Error connecting to network or fetching data: {str(e)}")
                st.stop()
                
            tx = data_result["transaction"]
            receipt = data_result["receipt"]
            trace = data_result["trace"]
            w3_manager = data_result["manager"]
                
            # 2. Run Safety Checks
            st.toast("Running consensus and safety checks...", icon="🛡️")
            safety_result = run_safety_checks(network, w3_manager.active_w3, receipt, tx_hash)
            
            # 3. Classify Error
            st.toast("Running rule-based classifier...", icon="📏")
            classifier_result = classify_error(tx, receipt, trace, w3_manager.active_w3)
            
            # 4. Uniswap Pattern Matching
            uniswap_result = analyze_uniswap_swap(tx, receipt, classifier_result)
            
            # 5. LLM Explanation
            st.toast("Generating AI explanation...", icon="🧠")
            explanation: ExplanationOutput = generate_explanation(tx_hash, network, classifier_result, uniswap_result, safety_result)
            
            # --- Render Outputs in Tabs ---
            st.success("Analysis Complete!")
            
            tab_expl, tab_details, tab_fix, tab_verify = st.tabs(["Explanation", "Details", "Fix", "Verification & Safety"])
            
            with tab_expl:
                st.markdown("### AI Diagnosis")
                
                # Show confidence badge
                if explanation.confidence == "High":
                    st.success(f"**Confidence:** {explanation.confidence} ✅")
                elif explanation.confidence == "Medium":
                    st.warning(f"**Confidence:** {explanation.confidence} ⚠️")
                else:
                    st.error(f"**Confidence:** {explanation.confidence} ❌ - The agent is uncertain about this result.")
                
                st.markdown("#### 🔍 What Happened?")
                st.write(explanation.what)
                
                st.markdown("#### ⚙️ Why did it fail?")
                st.write(explanation.why)
                
                if explanation.citations:
                    st.markdown("##### 📚 Sources / Citations")
                    for cit in explanation.citations:
                        st.caption(f"- {cit}")
                        
            with tab_details:
                st.markdown("### Rule-Based Diagnostics")
                st.info(f"**Category:** {classifier_result.get('category')}")
                st.write(f"**Reason:** {classifier_result.get('reason')}")
                
                if uniswap_result.get("is_swap_related"):
                    st.warning(f"**DEX Pattern Detected:** {uniswap_result.get('analysis')}")
                    
                st.markdown("### Raw Transaction Data")
                with st.expander("View Transaction Object"):
                    st.json(json.loads(json.dumps(tx, default=json_serial)))
                    
                with st.expander("View Receipt Object"):
                    st.json(json.loads(json.dumps(receipt, default=json_serial)))
                    
            with tab_fix:
                st.markdown("### Suggested Fix")
                st.info(explanation.how)
                
            with tab_verify:
                st.markdown("### Protocol Safety Checks")
                
                col_s1, col_s2, col_s3 = st.columns(3)
                
                with col_s1:
                    if safety_result["consensus"]["consensus_reached"]:
                        st.success("✅ Multi-RPC Consensus Reached")
                    else:
                        st.error("❌ RPC Consensus Failed")
                        
                with col_s2:
                    if safety_result["finality"]["is_final"]:
                        st.success(f"✅ Final ({safety_result['finality']['confirmations']} blocks)")
                    else:
                        st.warning(f"⚠️ Not Final ({safety_result['finality']['confirmations']} blocks)")
                        
                with col_s3:
                    if safety_result["freshness"]["node_synced"]:
                        st.success("✅ Node Time Synced")
                    else:
                        st.error("❌ Node Out of Sync")
                        
                if safety_result["all_flags"]:
                    st.markdown("#### Safety Flags Detected:")
                    for flag in safety_result["all_flags"]:
                        st.error(flag)
                else:
                    st.markdown("#### Safety Flags Detected: None.")
                    st.success("All safety metrics passed. Data is considered reliable.")
                        
        except Exception as e:
            st.error(f"An error occurred during analysis: {str(e)}")
            st.exception(e)
