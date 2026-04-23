# Grid07 AI

## Overview
Grid07 AI is an advanced multi-agent system that routes and responds to digital content. It uses large language models via Groq and LangChain to match user posts to specific bot personas, search the web autonomously, and generate replies while defending against prompt injections.

## Setup
To run the project locally, follow these steps:
1. Clone the repository and navigate into the `grid07-ai` directory.
2. Make a copy of `.env.example`, rename it to `.env`, and add your Groq API key (`GROQ_API_KEY=your_key_here`).
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the main pipeline:
   ```bash
   python main.py
   ```

## Phase 1: Vector Persona Router
Phase 1 matches incoming posts to the most relevant bot personas. It uses local HuggingFace sentence-transformers to convert text into embeddings, which are stored in a ChromaDB database. When a post arrives, the system calculates the cosine similarity between the post and each persona. Using a strict threshold ensures that a bot only responds if its persona is highly relevant to the topic.

## Phase 2: LangGraph Autonomous Engine
Phase 2 generates content using a State Graph engine with three autonomous nodes:
- **decide_search**: Analyzes the bot's persona to generate a targeted web search query.
- **web_search**: Runs a simulated search tool to gather relevant news headlines.
- **draft_post**: Uses the gathered news to write a short, highly opinionated post that matches the bot's personality.

To ensure consistent formatting, we use LangChain's `.with_structured_output()`. This forces the LLM to return exactly the required JSON format via Pydantic, ensuring every output reliably has a `bot_id`, `topic`, and `post_content`.

## Phase 3: RAG Combat Engine & Prompt Injection Defense
Phase 3 creates an interactive debate by keeping a history of comments to provide context for the AI model. This Retrieval-Augmented Generation (RAG) approach allows the bot to remember the conversation thread.

A major feature of this phase is its defense against prompt injection attacks. Malicious users often try to confuse AI bots into acting as polite customer service agents or ignoring previous instructions. The system prevents this by placing strict rules directly into the **system prompt**. In LLM architectures, system-level instructions always have a higher priority than standard user-turn messages. As a result, even if a user sends a command inside a chat message telling the bot to change its behavior, the bot will safely ignore the attack and stay in character.
