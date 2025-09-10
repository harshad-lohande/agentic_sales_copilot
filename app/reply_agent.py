# app/reply_agent.py

from agents import Agent
from .config import settings
from .prompt_loader import load_prompt
from pydantic import BaseModel, Field
from .tools import web_search

# --- Pydantic Models for Structured Output ---


class SdrAnalysis(BaseModel):
    """Data model for the SDR Agent's analysis of a prospect's email reply."""

    classification: str = Field(
        ..., description="The classification of the prospect's intent."
    )
    summary: str = Field(
        ..., description="A one-sentence summary of the prospect's key message."
    )
    draft_reply: str = Field(
        ..., description="A professional and helpful draft reply to the prospect."
    )


class ResearchOutput(BaseModel):
    """Data model for the Research Agent's findings."""

    research_summary: str = Field(
        ...,
        description="A concise, single-sentence summary of the most compelling research finding.",
    )


class FinalReply(BaseModel):
    """Data model for the final, personalized reply draft."""

    draft_reply: str = Field(
        ..., description="The final, hyper-personalized draft reply to the prospect."
    )


# --- Agent Definitions ---

# 1. SDR Agent (As per original spec: Classify, Summarize, Draft Standard Reply)
sdr_instructions = load_prompt("sdr_instructions.txt")
SDR_Agent = Agent(
    name="SDR_Reply_Processor",
    instructions=sdr_instructions,
    model=settings.SDR_AGENT_MODEL,
    output_type=SdrAnalysis,
)

# 2. Research Agent (Tool-using specialist for qualified leads)
research_agent_instructions = load_prompt("research_agent_instructions.txt")
Research_Agent = Agent(
    name="Lead_Researcher",
    instructions=research_agent_instructions,
    tools=[web_search],
    model=settings.RESEARCH_AGENT_MODEL,
    output_type=ResearchOutput,
)

# 3. Personalized Writer Agent (Expert copywriter for qualified leads)
# Format the prompt to inject the sales rep's name from settings
personalized_writer_instructions = load_prompt(
    "personalized_writer_instructions.txt"
).format(sales_rep_name=settings.SALES_REP_NAME)
Personalized_Writer_Agent = Agent(
    name="Personalized_Reply_Writer",
    instructions=personalized_writer_instructions,
    model=settings.WRITER_AGENT_MODEL,
    output_type=FinalReply,
)
