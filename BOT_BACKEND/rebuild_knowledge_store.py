from agentic_system.knowledge_store import rebuild_knowledge_store


if __name__ == "__main__":
    result = rebuild_knowledge_store(force=True)
    print("Knowledge store rebuild result:")
    for key, value in result.items():
        print(f"{key}: {value}")
