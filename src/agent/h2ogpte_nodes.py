"""h2oGPTe specific nodes for the credit renewal workflow."""
import os

from dotenv import load_dotenv
from h2ogpte import H2OGPTEAsync

# Load environment variables
load_dotenv()


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


async def rag_policy(state) -> dict:
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


async def rag_entity(state) -> dict:
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


async def rag_market(state) -> dict:
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


async def synthesize_recommendation(state) -> dict:
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
        return {"credit_memo": credit_memo}
    except Exception as e:
        return {"credit_memo": f"Synthesis failed: {str(e)}"}
