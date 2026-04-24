from agent.llm import call_llm

questions = [
    # "Is it safe to fish near Kochi today?",
    # "What is the price of Pomfret in Kozhikode market?",
    # "What government schemes help fishermen buy new boats?",
    # "Is it safe to fish near Alappuzha and what is the Sardine price there?",

    "i had a mishappen and lost my boat",
]

for q in questions:
    print("\n" + "=" * 60)
    print(f"Q: {q}")
    print("=" * 60)
    answer = call_llm(q)
    print(f"A: {answer}")
