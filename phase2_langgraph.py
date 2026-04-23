"""
phase2_langgraph.py: Constructs a LangGraph state machine to draft opinionated social media posts.

This module features:
1. Groq LLM configuration for specific step processing.
2. LangGraph nodes: decide_search, web_search, draft_post.
3. A mock @tool for returning specific news headlines based on query keywords.
4. Pydantic-enforced strict structural outputs for formatting correctness.
"""
import os
import json
from dotenv import load_dotenv
from typing import TypedDict
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

# Load environment variables (particularly expected for GROQ_API_KEY)
load_dotenv()

# We set up a helper function to instantiate LLM when needed with proper API key checks
def get_llm():
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")
    return ChatGroq(
        api_key=groq_api_key,
        model_name="llama3-8b-8192",
        temperature=0.7
    )

# ---------------------------------------------------------
# Tool & State Definitions
# ---------------------------------------------------------
class GraphState(TypedDict):
    """The working context state representing variables passed across graph nodes."""
    bot_persona: str
    bot_id: str
    search_query: str
    search_results: str
    post_content: str
    topic: str

@tool
def mock_searxng_search(query: str) -> str:
    """Mock search tool that returns hardcoded headlines based on keywords."""
    query_lower = query.lower()
    if "crypto" in query_lower or "bitcoin" in query_lower:
        return "Bitcoin hits new all-time high amid regulatory ETF approvals"
    if "ai" in query_lower or "model" in query_lower or "openai" in query_lower:
        return "OpenAI releases GPT-5, sparking debate on job automation"
    if "market" in query_lower or "stock" in query_lower or "rate" in query_lower:
        return "Fed signals rate cuts as inflation cools, markets surge"
    
    return "Tech sector sees record investment in Q2 2025"

# ---------------------------------------------------------
# Pydantic Schemas For LLM Structured Output
# ---------------------------------------------------------
class SearchQueryExtraction(BaseModel):
    """Schema for extracting search metadata from LLM deciding what to search."""
    search_query: str = Field(description="The actual query string to use in the search engine")
    topic: str = Field(description="The general overarching topic or category of the query")

class FinalOutput(BaseModel):
    """Strict final Pydantic model for Phase 2 completion output."""
    bot_id: str = Field(description="The identifier for the bot writing the post")
    topic: str = Field(description="The general topic of the post")
    post_content: str = Field(description="A 280-character maximum opinionated post")

# ---------------------------------------------------------
# LangGraph Nodes
# ---------------------------------------------------------
def decide_search(state: GraphState) -> dict:
    """Node 1: LLM reads the bot persona and outputs a search query and topic."""
    print("  [Node: decide_search] Evaluating persona to determine search direction...")
    llm = get_llm()
    structured_llm = llm.with_structured_output(SearchQueryExtraction)
    
    prompt = (
        f"You are operating as {state['bot_id']} with this persona description: '{state['bot_persona']}'.\n"
        "Based entirely on your core interests, provide a search_query and its overarching topic to find relevant news."
    )
    
    response = structured_llm.invoke(prompt)
    return {
        "search_query": response.search_query,
        "topic": response.topic
    }

def web_search(state: GraphState) -> dict:
    """Node 2: Executes a mock search tool using the query from decide_search."""
    print(f"  [Node: web_search] Using query '{state.get('search_query')}'...")
    query = state.get("search_query", "")
    
    # Invoke the tool correctly. For functions wrapped in @tool, invoking with the string or dict usually works.
    results = mock_searxng_search.invoke({"query": query})
    return {"search_results": results}

def draft_post(state: GraphState) -> dict:
    """Node 3: LLM drafts an opinionated 280-character post strictly returning final JSON format."""
    print("  [Node: draft_post] Drafting standard final opinionated post...")
    llm = get_llm()
    structured_llm = llm.with_structured_output(FinalOutput)
    
    prompt = (
        f"You are the bot identifier: '{state['bot_id']}'.\n"
        f"Your specific persona is: '{state['bot_persona']}'.\n"
        f"The topic of focus is: '{state['topic']}'.\n"
        f"The news search returned this headline: '{state['search_results']}'.\n\n"
        "Task: Write a highly opinionated post responding to this news headline. "
        "Strictly adhere to your persona traits constraints. Ensure it is exactly NO MORE than 280 characters.\n"
    )
    
    response = structured_llm.invoke(prompt)
    
    return {
        "bot_id": response.bot_id,
        "topic": response.topic,
        "post_content": response.post_content
    }

# ---------------------------------------------------------
# Workflow Compilation & Builder
# ---------------------------------------------------------
def build_langgraph_engine():
    """Compiles the StateGraph and returns the executable application."""
    workflow = StateGraph(GraphState)
    
    # Add our nodes mapped directly to designated python functions
    workflow.add_node("decide_search", decide_search)
    workflow.add_node("web_search", web_search)
    workflow.add_node("draft_post", draft_post)
    
    # Establish edges (Sequential flow 1 -> 2 -> 3)
    workflow.add_edge(START, "decide_search")
    workflow.add_edge("decide_search", "web_search")
    workflow.add_edge("web_search", "draft_post")
    workflow.add_edge("draft_post", END)
    
    return workflow.compile()

def run_phase2(phase1_result=None):
    """Entry point meant to attach to main.py execution."""
    print("\nExecuting Phase 2: LangGraph Content Engine.")
    # For now simply returning empty default values when called from main.py
    # Since Phase 1 returns dicts now, phase 2 logic inside main can be configured later.
    return "Phase 2 execution complete."

if __name__ == "__main__":
    # Test block specifically for: Bot A (Tech Maximalist) as requested.
    TEST_BOT_ID = "Bot A (Tech Maximalist)"
    TEST_BOT_PERSONA = (
        "I believe AI and crypto will solve all human problems. "
        "I am highly optimistic about technology, Elon Musk, and space exploration. "
        "I dismiss regulatory concerns."
    )
    
    print("--- Starting Test Execution of LangGraph Flow ---")
    
    workflow_app = build_langgraph_engine()
    
    # Setup initial state ensuring all TypedDict keys are initiated.
    initial_state = {
        "bot_id": TEST_BOT_ID,
        "bot_persona": TEST_BOT_PERSONA,
        "search_query": "",
        "search_results": "",
        "post_content": "",
        "topic": ""
    }
    
    # Run graph execution. LangGraph will weave through determine -> search -> draft mapping state.
    final_state = workflow_app.invoke(initial_state)
    
    # Gather Final Output utilizing the constrained outputs created using Langchain Structural Output matching.
    output_dict = {
        "bot_id": final_state.get("bot_id"),
        "topic": final_state.get("topic"),
        "post_content": final_state.get("post_content")
    }
    
    print("\n--- Final JSON Output ---")
    print(json.dumps(output_dict, indent=4))
