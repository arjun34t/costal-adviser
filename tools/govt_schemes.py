import os
import glob

SCHEMES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "schemes")

def get_scheme_info(keyword: str) -> str:
    """
    Since there are only a few scheme files (~1.5 KB total), we can just 
    return all of them to the LLM. The LLM has a large enough context 
    window to instantly pluck out the relevant scheme based on the user's query.
    This eliminates the need for heavy local Vector DBs / PyTorch dependencies.
    """
    txt_files = glob.glob(os.path.join(SCHEMES_DIR, "*.txt"))
    if not txt_files:
        return "No government scheme data available."

    parts = []
    for filepath in txt_files:
        source = os.path.basename(filepath).replace(".txt", "").replace("_", " ").title()
        with open(filepath, "r", encoding="utf-8") as f:
            doc = f.read().strip()
        parts.append(f"[{source}]\n{doc}")

    return "\n\n".join(parts)

if __name__ == "__main__":
    print("\n--- Test query: 'accident compensation for fishermen' ---")
    print(get_scheme_info("accident compensation for fishermen"))
