"""Cenário de mentira para os testes: um projeto cadastrado e duas conversas do Claude Code, tudo dentro da pasta do teste.
Assim os testes dão o mesmo resultado em qualquer computador e não leem as conversas de verdade."""
import json, os


def preparar(pasta, amb):
    loja = os.path.join(pasta, "projetos", "loja")
    os.makedirs(loja, exist_ok=True)
    os.makedirs(os.path.join(pasta, "dados"), exist_ok=True)
    with open(os.path.join(pasta, "dados", "projetos.json"), "w", encoding="utf-8") as f:
        json.dump([{"nome": "Loja", "apelidos": ["loja", "lojinha"], "pasta": loja}], f, ensure_ascii=False)
    sessoes = os.path.join(pasta, "sessoes")
    for i, titulo in enumerate(("Loja: carrinho de compras", "Loja: tela de entrada"), 1):
        d = os.path.join(sessoes, f"projeto-{i}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"00000000-0000-0000-0000-00000000000{i}.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "custom-title", "customTitle": titulo}) + "\n")
            f.write(json.dumps({"type": "user", "cwd": loja}) + "\n")
    amb["JARVIS_SESSOES"] = sessoes
    return loja
