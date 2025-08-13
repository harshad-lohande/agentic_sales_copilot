# app/reply_agent.py

from agents import Agent
from .config import settings
from .prompt_loader import load_prompt
from pydantic import BaseModel, Field

# Define the structured output model using Pydantic
class SdrAnalysis(BaseModel):
    """Data model for the SDR Agent's analysis of a prospect's email reply."""
    classification: str = Field(..., description="The classification of the prospect's intent.")
    summary: str = Field(..., description="A one-sentence summary of the prospect's key message.")
    draft_reply: str = Field(..., description="A professional and helpful draft reply to the prospect.")


# Load the instructions from the file
sdr_instructions = load_prompt("sdr_instructions.txt")

# Update the Agent to use the structured output model
SDR_Agent = Agent(
    name="SDR_Reply_Processor",
    instructions=sdr_instructions,
    model=settings.SDR_AGENT_MODEL,
    output_type=SdrAnalysis # This tells the agent to always return an SdrAnalysis object
)