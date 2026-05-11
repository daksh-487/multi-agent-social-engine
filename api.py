"""
api.py: Flask REST API server for Grid07 AI — exposes all 3 phases as HTTP endpoints.
"""
import json
import os
import traceback
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────
# Lazy imports to avoid startup crash when
# sentence-transformers loads on first call
# ─────────────────────────────────────────
_router_ready = False
_phase1_route = None
_phase1_personas = None

def _init_phase1():
    global _router_ready, _phase1_route, _phase1_personas
    if not _router_ready:
        from phase1_router import route_post_to_bots, BOT_PERSONAS
        _phase1_route   = route_post_to_bots
        _phase1_personas = BOT_PERSONAS
        _router_ready   = True


# ─────────────────────────────────────────
# Health
# ─────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    key_set = bool(os.environ.get("OPENAI_API_KEY"))
    return jsonify({"status": "ok", "groq_key_configured": key_set})


# ─────────────────────────────────────────
# Phase 1 — Vector Persona Router
# ─────────────────────────────────────────
@app.route("/api/phase1/route", methods=["POST"])
def phase1_route():
    data = request.get_json(silent=True) or {}
    post_content = data.get("post_content", "").strip()
    threshold    = float(data.get("threshold", 0.25))

    if not post_content:
        return jsonify({"error": "post_content is required"}), 400

    try:
        _init_phase1()
        matches = _phase1_route(post_content=post_content, threshold=threshold)
        return jsonify({
            "post_content": post_content,
            "threshold":    threshold,
            "matches":      matches,
            "all_personas": _phase1_personas
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────
# Phase 2 — LangGraph Content Engine
# ─────────────────────────────────────────
@app.route("/api/phase2/generate", methods=["POST"])
def phase2_generate():
    data    = request.get_json(silent=True) or {}
    bot_id  = data.get("bot_id", "")
    persona = data.get("bot_persona", "")

    if not bot_id or not persona:
        return jsonify({"error": "bot_id and bot_persona are required"}), 400

    if not os.environ.get("OPENAI_API_KEY"):
        return jsonify({"error": "OPENAI_API_KEY is not configured on the server"}), 503

    try:
        from phase2_langgraph import build_langgraph_engine
        workflow_app = build_langgraph_engine()
        initial_state = {
            "bot_id":       bot_id,
            "bot_persona":  persona,
            "search_query": "",
            "search_results": "",
            "post_content": "",
            "topic": ""
        }
        final_state = workflow_app.invoke(initial_state)
        return jsonify({
            "bot_id":       final_state.get("bot_id"),
            "topic":        final_state.get("topic"),
            "search_query": final_state.get("search_query"),
            "search_results": final_state.get("search_results"),
            "post_content": final_state.get("post_content")
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────
# Phase 3 — RAG Combat Engine
# ─────────────────────────────────────────
@app.route("/api/phase3/defend", methods=["POST"])
def phase3_defend():
    data            = request.get_json(silent=True) or {}
    bot_persona     = data.get("bot_persona", "").strip()
    parent_post     = data.get("parent_post", "").strip()
    comment_history = data.get("comment_history", [])
    human_reply     = data.get("human_reply", "").strip()

    if not all([bot_persona, parent_post, human_reply]):
        return jsonify({"error": "bot_persona, parent_post, and human_reply are required"}), 400

    if not os.environ.get("OPENAI_API_KEY"):
        return jsonify({"error": "OPENAI_API_KEY is not configured on the server"}), 503

    try:
        from phase3_rag import generate_defense_reply
        reply = generate_defense_reply(
            bot_persona=bot_persona,
            parent_post=parent_post,
            comment_history=comment_history,
            human_reply=human_reply
        )
        return jsonify({"reply": reply})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
