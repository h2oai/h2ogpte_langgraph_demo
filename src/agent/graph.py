"""LangGraph workflow for credit renewal processing with RAG and HITL."""
import os
from typing import TypedDict

from dotenv import load_dotenv
from h2ogpte import H2OGPTEAsync
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import interrupt

# Load environment variables from .env file
load_dotenv()


class CreditRenewalInput(TypedDict):
    """Input schema for the credit renewal workflow - only what users need to provide."""
    borrower_id: str
    sector: str


class OverallState(TypedDict):
    """Internal state schema for the credit renewal workflow."""
    borrower_id: str
    sector: str
    policy_query: str
    entity_query: str
    market_query: str
    policy_pack: str
    entity_pack: str
    market_pack: str
    credit_memo: str
    approved_memo: str
    rerun_policy: bool
    rerun_entity: bool
    rerun_market: bool
    # Individual RAG acceptance fields
    accept_policy: bool
    accept_entity: bool
    accept_market: bool
    # Final approval field
    accept_synthesis: bool


async def get_h2ogpte_client() -> H2OGPTEAsync:
    """Get configured h2oGPTE async client."""
    return H2OGPTEAsync(
        address=os.getenv('H2OGPTE_URL', 'https://h2ogpte.genai.h2o.ai'),  # default to freemium
        api_key=os.getenv('H2OGPTE_API_KEY')
    )


async def query_h2ogpte_rag(query: str, collection_id: str) -> str:
    """Query h2oGPTE RAG with given collection ID."""
    client = await get_h2ogpte_client()
    chat_session_id = await client.create_chat_session(collection_id=collection_id)

    async with client.connect(chat_session_id) as session:
        reply = await session.query(
            query,
            timeout=3600,
            llm_args={
                "use_agent": False,
                "agent_accuracy": "standard"
            }
        )
    return reply.content


async def query_h2ogpte_llm(prompt: str) -> str:
    """Query h2oGPTE LLM without RAG."""
    client = await get_h2ogpte_client()
    chat_session_id = await client.create_chat_session()

    async with client.connect(chat_session_id) as session:
        reply = await session.query(
            prompt,
            timeout=3600,
            llm_args={
                "use_agent": False,
                "agent_accuracy": "standard"
            }
        )
    return reply.content


async def ingest_renewal_alert(state: OverallState) -> OverallState:
    """Ingest node: receives renewal trigger and sets up state."""
    # Parse input and set up queries for RAG retrieval
    borrower_id = state.get('borrower_id', 'TechManufacture Inc')
    sector = state.get('sector', 'Advanced Manufacturing')

    state['policy_query'] = f"Credit policy and underwriting guidelines for {borrower_id} in {sector} sector"
    state['entity_query'] = f"Financial data, credit history, and risk profile for {borrower_id}"
    state['market_query'] = f"Market conditions, sector analysis, and economic indicators for {sector} sector"

    return state


async def rag_policy(state: OverallState) -> OverallState:
    """RAG-Policy node: retrieves policy context."""
    policy_collection_id = os.getenv('POLICY_COLLECTION_ID')
    if not policy_collection_id:
        raise ValueError(
            "POLICY_COLLECTION_ID environment variable not set. "
            "Please check the README for setup instructions and ensure your .env file is configured correctly."
        )

    try:
        policy_content = await query_h2ogpte_rag(state['policy_query'], policy_collection_id)
        return {
            "policy_pack": f"Policy Analysis:\n{policy_content}",
            "accept_policy": False  # Reset acceptance when rerunning
        }
    except Exception as e:
        return {
            "policy_pack": f"Policy retrieval failed: {str(e)}",
            "accept_policy": False  # Reset acceptance when rerunning
        }


async def rag_entity(state: OverallState) -> OverallState:
    """RAG-Entity node: retrieves borrower/entity data."""
    entity_collection_id = os.getenv('ENTITY_COLLECTION_ID')
    if not entity_collection_id:
        raise ValueError(
            "ENTITY_COLLECTION_ID environment variable not set. "
            "Please check the README for setup instructions and ensure your .env file is configured correctly."
        )

    try:
        entity_content = await query_h2ogpte_rag(state['entity_query'], entity_collection_id)
        return {
            "entity_pack": f"Entity Analysis:\n{entity_content}",
            "accept_entity": False  # Reset acceptance when rerunning
        }
    except Exception as e:
        return {
            "entity_pack": f"Entity retrieval failed: {str(e)}",
            "accept_entity": False  # Reset acceptance when rerunning
        }


async def rag_market(state: OverallState) -> OverallState:
    """RAG-Market node: retrieves market/sector data."""
    market_collection_id = os.getenv('MARKET_COLLECTION_ID')
    if not market_collection_id:
        raise ValueError(
            "MARKET_COLLECTION_ID environment variable not set. "
            "Please check the README for setup instructions and ensure your .env file is configured correctly."
        )

    try:
        market_content = await query_h2ogpte_rag(state['market_query'], market_collection_id)
        return {
            "market_pack": f"Market Analysis:\n{market_content}",
            "accept_market": False  # Reset acceptance when rerunning
        }
    except Exception as e:
        return {
            "market_pack": f"Market retrieval failed: {str(e)}",
            "accept_market": False  # Reset acceptance when rerunning
        }


async def synthesize_recommendation(state: OverallState) -> OverallState:
    """Synthesis node: compiles packs, drafts memo."""
    synthesis_prompt = f"""
    Based on the following information, create a comprehensive credit renewal memo:

    Policy Context:
    {state['policy_pack']}

    Entity Analysis:
    {state['entity_pack']}

    Market Analysis:
    {state['market_pack']}

    Please provide:
    1. Credit rating recommendation
    2. Key covenants and conditions
    3. Pricing recommendations
    4. Risk factors and mitigants
    5. Citations and supporting evidence

    Format as a professional credit memo.
    """

    try:
        credit_memo = await query_h2ogpte_llm(synthesis_prompt)
        state['credit_memo'] = credit_memo
    except Exception as e:
        state['credit_memo'] = f"Synthesis failed: {str(e)}"

    return state


def hitl_policy_review(state: OverallState) -> OverallState:
    """HITL node: review policy RAG output."""
    policy_summary = f"""
POLICY RAG REVIEW:

📋 POLICY ANALYSIS:
{state.get('policy_pack', 'Not available')}

Accept response?
"""

    # Use interrupt with the policy pack for human review
    accept_policy = interrupt({
        "policy_pack": state.get('policy_pack', 'Not available'),
        "message": policy_summary
    })

    return {
        "accept_policy": accept_policy
    }


def hitl_entity_review(state: OverallState) -> OverallState:
    """HITL node: review entity RAG output."""
    entity_summary = f"""
ENTITY RAG REVIEW:

🏢 ENTITY ANALYSIS:
{state.get('entity_pack', 'Not available')}

Accept response?
"""

    # Use interrupt with the entity pack for human review
    accept_entity = interrupt({
        "entity_pack": state.get('entity_pack', 'Not available'),
        "message": entity_summary
    })

    return {
        "accept_entity": accept_entity
    }


def hitl_market_review(state: OverallState) -> OverallState:
    """HITL node: review market RAG output."""
    market_summary = f"""
MARKET RAG REVIEW:

📈 MARKET ANALYSIS:
{state.get('market_pack', 'Not available')}

Accept response?
"""

    # Use interrupt with the market pack for human review
    accept_market = interrupt({
        "market_pack": state.get('market_pack', 'Not available'),
        "message": market_summary
    })

    return {
        "accept_market": accept_market
    }


def hitl_final_approval(state: OverallState) -> OverallState:
    """HITL node: final approval of synthesized memo."""
    approval_summary = f"""
FINAL APPROVAL REQUIRED - CREDIT RENEWAL MEMO:

📄 CREDIT MEMO:
{state.get('credit_memo', 'Not available')}

Accept response?
"""

    # Use interrupt with the credit memo for human review
    accept_synthesis = interrupt({
        "credit_memo": state.get('credit_memo', 'Not available'),
        "message": approval_summary
    })

    return {
        "accept_synthesis": accept_synthesis
    }


def should_rerun_policy(state: OverallState) -> bool:
    """Check if policy RAG should be rerun."""
    # If not accepted, then rerun
    return not state.get('accept_policy', False)


def should_rerun_entity(state: OverallState) -> bool:
    """Check if entity RAG should be rerun."""
    # If not accepted, then rerun
    return not state.get('accept_entity', False)


def should_rerun_market(state: OverallState) -> bool:
    """Check if market RAG should be rerun."""
    # If not accepted, then rerun
    return not state.get('accept_market', False)


def should_synthesize(state: OverallState) -> bool:
    """Check if all RAGs are complete and ready for synthesis."""
    # All RAGs must be accepted to proceed to synthesis
    return all([
        state.get('accept_policy', False),
        state.get('accept_entity', False),
        state.get('accept_market', False)
    ])


# Create the graph with input schema
graph = StateGraph(OverallState, input_schema=CreditRenewalInput)
graph.add_node("Ingest", ingest_renewal_alert)
graph.add_node("RAG_Policy", rag_policy)
graph.add_node("RAG_Entity", rag_entity)
graph.add_node("RAG_Market", rag_market)
graph.add_node("HITL_Policy", hitl_policy_review)
graph.add_node("HITL_Entity", hitl_entity_review)
graph.add_node("HITL_Market", hitl_market_review)
graph.add_node("Synthesize", synthesize_recommendation)
graph.add_node("HITL_Final", hitl_final_approval)

# Set entrypoint
graph.set_entry_point("Ingest")

# Ingest → three RAGs in parallel
graph.add_edge("Ingest", "RAG_Policy")
graph.add_edge("Ingest", "RAG_Entity")
graph.add_edge("Ingest", "RAG_Market")

# Each RAG → its individual HITL review
graph.add_edge("RAG_Policy", "HITL_Policy")
graph.add_edge("RAG_Entity", "HITL_Entity")
graph.add_edge("RAG_Market", "HITL_Market")

# Each HITL → conditional routing (rerun RAG or proceed to synthesis)
graph.add_conditional_edges(
    "HITL_Policy",
    lambda state: "RAG_Policy" if should_rerun_policy(state) else "Synthesize",
    {
        "RAG_Policy": "RAG_Policy",
        "Synthesize": "Synthesize"
    }
)

graph.add_conditional_edges(
    "HITL_Entity",
    lambda state: "RAG_Entity" if should_rerun_entity(state) else "Synthesize",
    {
        "RAG_Entity": "RAG_Entity",
        "Synthesize": "Synthesize"
    }
)

graph.add_conditional_edges(
    "HITL_Market",
    lambda state: "RAG_Market" if should_rerun_market(state) else "Synthesize",
    {
        "RAG_Market": "RAG_Market",
        "Synthesize": "Synthesize"
    }
)

# Synthesis → Final HITL
graph.add_edge("Synthesize", "HITL_Final")

# Final HITL → conditional routing (back to synthesis if not accepted)
graph.add_conditional_edges(
    "HITL_Final",
    lambda state: "Synthesize" if not state.get('accept_synthesis', False) else "__end__",
    {
        "Synthesize": "Synthesize",
        "__end__": "__end__"
    }
)


def run_credit_renewal(borrower_id: str, sector: str):
    """Simplified interface for running credit renewal workflow."""
    # Create checkpointer
    checkpointer = MemorySaver()

    # Compile the graph with checkpointer
    compiled_graph = graph.compile(checkpointer=checkpointer)

    # Create input with defaults for internal fields
    input_data = {
        "borrower_id": borrower_id,
        "sector": sector,
        # These will be populated by the workflow
        "policy_query": "",
        "entity_query": "",
        "market_query": "",
        "policy_pack": "",
        "entity_pack": "",
        "market_pack": "",
        "credit_memo": "",
        "approved_memo": "",
        "rerun_policy": False,
        "rerun_entity": False,
        "rerun_market": False,
        "accept_policy": False,
        "accept_entity": False,
        "accept_market": False,
        "accept_synthesis": False
    }

    # Run the graph until interrupt
    config = {"configurable": {"thread_id": f"credit_renewal_{borrower_id}"}}
    result = compiled_graph.invoke(input_data, config=config)
    return result, compiled_graph, config


def main():
    """Run example input and execution."""
    # Simple demo - just provide borrower and sector
    result, compiled_graph, config = run_credit_renewal(
        borrower_id="TechManufacture Inc",
        sector="Advanced Manufacturing"
    )


if __name__ == "__main__":
    main()
