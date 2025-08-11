# app/reply_agent.py

from agents import Agent
from .config import settings
from .prompt_loader import load_prompt

sdr_instructions = load_prompt("sdr_instructions.txt")

SDR_Agent = Agent(
    name="SDR_Reply_Processor",
    instructions=sdr_instructions,
    model=settings.SDR_AGENT_MODEL # We use a powerful model for nuanced understanding
)