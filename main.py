import os
import sys

from config.settings import GOOGLE_API_KEY, CHROMA_PERSIST_DIR
from db.sql_store import init_db
from db.vector_store import build_vector_store, load_vector_store
from agents.rag_chain import build_agent
from guardrails.pii_filter import redact_pii
from langchain_core.messages import HumanMessage

def setup():
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found in .env file.")
        sys.exit(1)

    print("Initializing SQLite database...")
    init_db()

    if not os.path.exists(CHROMA_PERSIST_DIR):
        print("Building vector store (first run, this embeds the parking documents)...")
        build_vector_store()
        print("Vector store ready.")
    else:
        load_vector_store()
        print("Vector store loaded from disk.")


def main():
    setup()

    print("\n--- CityPark Central Parking Assistant ---")
    print("Type your question or 'quit' to exit.\n")

    agent = build_agent()
    messages = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        messages.append(HumanMessage(content=user_input))

        result = agent.invoke({"messages": messages})

        ai_messages = [
            m for m in result["messages"]
            if hasattr(m, "type") and m.type == "ai" and m.content
        ]

        if not ai_messages:
            response = "I couldn't generate a response."
        else:
            content = ai_messages[-1].content
            if isinstance(content, list):
                response = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            else:
                response = str(content)

        if response:
            response = redact_pii(response)

        print(f"\nAssistant: {response}\n")

        messages = result["messages"]


if __name__ == "__main__":
    main()
