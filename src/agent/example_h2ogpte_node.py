"""Example h2oGPTe node."""
import os

from dotenv import load_dotenv
from h2ogpte import H2OGPTEAsync

# Load environment variables
load_dotenv()


async def example_h2ogpte_node(state) -> dict:
    """Example h2oGPTe node."""
    client = await H2OGPTEAsync(
        address=os.getenv('H2OGPTE_URL', 'https://h2ogpte.genai.h2o.ai'),  # default to freemium
        api_key=os.getenv('H2OGPTE_API_KEY')
    )

    chat_session_id = await client.create_chat_session()

    async with client.connect(chat_session_id) as session:
        reply = await session.query("What is the capital of France?")

    state['reply'] = reply

    return state
