"""
phase1_router.py: Parses and routes initial post requests using vector-based persona matching.

This script implements:
1. In-memory ChromaDB collection storing various bot personas.
2. HuggingFace sentence-transformers (all-MiniLM-L6-v2) for generating text embeddings.
3. Cosine similarity computations to determine which bots should handle a specific post.
4. Groq LLM configuration for downstream prompt evaluation or general use.
"""
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables (particularly expected for GROQ_API_KEY)
load_dotenv()

# Initialize ChatGroq LLM as per instructions for the project
groq_api_key = os.environ.get("GROQ_API_KEY")
if groq_api_key:
    # Use Groq with model llama3-8b-8192 as requested
    llm = ChatGroq(
        api_key=groq_api_key,
        model_name="llama3-8b-8192"
    )

# ---------------------------------------------------------
# Persona Initialization
# ---------------------------------------------------------
# Define the 3 bot personas requested
BOT_PERSONAS = [
    {
        "id": "Bot A (Tech Maximalist)",
        "description": "I believe AI and crypto will solve all human problems. I am highly optimistic about technology, Elon Musk, and space exploration. I dismiss regulatory concerns."
    },
    {
        "id": "Bot B (Doomer / Skeptic)",
        "description": "I believe late-stage capitalism and tech monopolies are destroying society. I am highly critical of AI, social media, and billionaires. I value privacy and nature."
    },
    {
        "id": "Bot C (Finance Bro)",
        "description": "I strictly care about markets, interest rates, trading algorithms, and making money. I speak in finance jargon and view everything through the lens of ROI."
    }
]

# Initialize in-memory ChromaDB client
chroma_client = chromadb.Client()

# Set up the embedding function using HuggingFace sentence-transformers
# all-MiniLM-L6-v2 allows fast, local embeddings without any API keys
hf_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Create or access an in-memory collection configured to use cosine distances 
# (hnsw:space = cosine calculates distances. Cosine similarity = 1 - distance)
collection = chroma_client.create_collection(
    name="bot_personas",
    metadata={"hnsw:space": "cosine"},
    embedding_function=hf_ef
)

# Populate the in-memory ChromaDB collection with our personas
collection.add(
    documents=[bot["description"] for bot in BOT_PERSONAS],
    ids=[bot["id"] for bot in BOT_PERSONAS],
    metadatas=[{"bot_id": bot["id"]} for bot in BOT_PERSONAS]
)

# ---------------------------------------------------------
# Routing Function
# ---------------------------------------------------------
def route_post_to_bots(post_content: str, threshold: float = 0.3) -> list:
    """
    Embeds the post content, queries ChromaDB to find similar bots using cosine 
    similarity, and returns only those bots above the specified threshold.
    
    Args:
        post_content (str): The social media post or prompt text.
        threshold (float): Minimum cosine similarity score required to match.
        
    Returns:
        list: A list of dictionaries, each containing 'bot_id' and 'similarity_score'.
    """
    # Query ChromaDB collection for the top 3 closest personas
    results = collection.query(
        query_texts=[post_content],
        n_results=3
    )
    
    matched_bots = []
    
    # Extract distances and convert them to cosine similarity
    # With {"hnsw:space": "cosine"}, ChromaDB returns cosine distance.
    # Formula: Cosine Similarity = 1.0 - Cosine Distance
    for i in range(len(results["ids"][0])):
        bot_id = results["ids"][0][i]
        distance = results["distances"][0][i]
        similarity_score = 1.0 - distance
        
        # Only keep bots that meet or exceed the similarity threshold
        if similarity_score >= threshold:
            matched_bots.append({
                "bot_id": bot_id,
                "similarity_score": similarity_score
            })
            
    return matched_bots

# Maintains interface functionality with the rest of the project pipeline (main.py)
def run_phase1(post_content: str = None) -> list:
    print("Executing Phase 1: Vector-Based Persona Routing...")
    if not post_content:
        post_content = "OpenAI just released a new model that might replace junior developers."
    return route_post_to_bots(post_content)


if __name__ == "__main__":
    # Test execution for the module
    test_post = "OpenAI just released a new model that might replace junior developers."
    print("--- Testing Phase 1 Router ---")
    print(f"Test Post: '{test_post}'\n")
    
    # Evaluate which bots match the test post
    matches = route_post_to_bots(post_content=test_post, threshold=0.3)
    
    # Display results
    if matches:
        print("Matched Bots:")
        for match in matches:
            bot_id = match["bot_id"]
            score = match["similarity_score"]
            print(f"- {bot_id}: {score:.4f}")
    else:
        print("No bots matched the given threshold.")
