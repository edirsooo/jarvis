"""Claude Code de mentira para testar o Jarvis sem gastar cota.
- Com --input-format stream-json: faz o papel do cérebro (responde JSON conforme palavras do pedido).
- Sem isso: faz o papel de uma missão (marcos, um arquivo de entrega, RESULTADO: OK). Guarda os argumentos em trabalho\\args.txt.
"""
import json, os, re, sys, time, uuid

args = sys.argv[1:]
sys.stdout.reconfigure(encoding="utf-8")


def sai(ev):
    sys.stdout.write(json.dumps(ev, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def cerebro():
    for linha in sys.stdin.buffer:
        try:
            msg = json.loads(linha.decode("utf-8"))
            txt = msg["message"]["content"]
        except Exception:
            continue
        ult = txt.strip().split("\n")[-1]
        b = txt.lower()
        ub = ult.lower()
        time.sleep(float(os.environ.get("FALSO_PENSA", "0.6")))
        r = {"fala": "Estou aqui.", "acoes": []}
        if "conteúdo da missão" in ub:      # o que a ação "ler" trouxe: responde se o texto da entrega chegou
            r = {"fala": "Li a página: " + ("tem o texto" if ("Arquivo " in ult and "Resumo do aprendiz" in ult) else "sem o texto"), "acoes": []}
        elif "redigir a missão" in b or "redigir a missao" in b:
            r = {"fala": "", "acoes": [{"tipo": "processo", "id": "prospeccao", "parametros": {"nicho": "academias", "cidade": "Valinhos, SP"},
                                        "pedido": "Prospecção de academias em Valinhos (redigida pelo Claude)", "titulo": "Prospecção redigida"}]}
        elif ub.startswith("[sistema] a missão") and "passou do tempo" in ub:
            r = {"fala": "A missão passou do tempo. Deixo seguir?", "acoes": []}
        elif ub.startswith("[sistema]"):
            r = {"fala": "O site ficou pronto. Quer que eu escreva o e-mail?", "acoes": []}
        elif "conversa" in ub and re.search(r"conversa (\d+)", ub):
            n = int(re.search(r"conversa (\d+)", ub).group(1))
            r = {"fala": "Assim será.", "acoes": [{"tipo": "conversa", "numero": n, "instrucao": "Continue o desenvolvimento.", "titulo": "Conversa continuada"}]}
        elif re.search(r"na (miss[aã]o )?(\d+)", ub):
            n = int(re.search(r"na (?:miss[aã]o )?(\d+)", ub).group(1))
            r = {"fala": "Ajustando.", "acoes": [{"tipo": "continuar", "missao": n, "instrucao": "Ajuste: " + ult.split("]", 1)[-1].strip()}]}
        elif "prospec" in ub:
            r = {"fala": "Está a caminho. O aprendiz vai abrir o Maps e depois montar a página com muito cuidado. Depois eu aviso.",
                 "acoes": [{"tipo": "processo", "id": "prospeccao", "parametros": {"nicho": "academias", "cidade": "Campinas, SP"},
                            "pedido": "Prospecção de academias", "titulo": "Prospecção de academias"}]}
        elif "na loja" in ub:
            r = {"fala": "Feito, já começou.", "acoes": [{"tipo": "processo", "id": "programar", "projeto": "Loja",
                                                          "parametros": {"tarefa": "corrigir o botão de vender"}, "pedido": "Corrigir o botão de vender", "titulo": "Botão de vender"}]}
        elif "o que tem no site" in ub:
            r = {"fala": "Lendo.", "acoes": [{"tipo": "ler", "assunto": "academias", "entrega": "site", "pergunta": "o que tem no site"}]}
        elif "abre o programa" in ub:
            r = {"fala": "Abrindo.", "acoes": [{"tipo": "rapida", "alvo": os.environ.get("FALSO_EXE", "")}]}
        elif "abre o site" in ub:
            r = {"fala": "Aqui está.", "acoes": [{"tipo": "abrir", "assunto": "academias", "entrega": "site"}]}
        elif "pelo nome" in ub:
            r = {"fala": "Só pelo nome, então.", "acoes": [{"tipo": "escuta", "modo": "nome"}]}
        elif "todo dia" in ub:
            r = {"fala": "Agendado.", "acoes": [{"tipo": "agendar", "processo": "resumo_do_dia", "hora": "8:00", "dias": "todos"}]}
        elif "salva isso como processo" in ub:
            r = {"fala": "Salvo.", "acoes": [{"tipo": "salvar_processo", "nome": "Teste de processo", "quando": "processo criado pelo teste"}]}
        elif "youtube" in ub:
            r = {"fala": "Abrindo.", "acoes": [{"tipo": "rapida", "alvo": "https://www.youtube.com"}]}
        elif "não é contigo" in ub:
            r = {"fala": "", "acoes": [{"tipo": "dormir"}]}
        elif "quanto" in ub and "?" in ub:
            r = {"fala": "São trezentos e noventa e um. É a conta de dezessete vezes vinte e três. Posso conferir de outro jeito. E ainda explico o método.", "acoes": []}
        texto = json.dumps(r, ensure_ascii=False)
        sai({"type": "assistant", "message": {"content": [{"type": "text", "text": texto}]}})
        sai({"type": "result", "result": texto, "is_error": False})


def missao():
    pasta = os.environ.get("JARVIS_MISSAO") or os.getcwd()
    pedido = sys.stdin.buffer.read().decode("utf-8", "replace")
    os.makedirs(os.path.join(pasta, "trabalho"), exist_ok=True)
    regras = ""
    if "--append-system-prompt-file" in args:
        try:
            with open(args[args.index("--append-system-prompt-file") + 1], encoding="utf-8") as f:
                regras = f.read()
        except Exception as e:
            regras = f"(não li o arquivo de regras: {e})"
    with open(os.path.join(pasta, "trabalho", "args.txt"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"args": args, "cwd": os.getcwd(), "pedido": pedido, "regras": regras}, ensure_ascii=False) + "\n")
    retomando = "--resume" in args
    sid = str(uuid.uuid4())
    sai({"type": "system", "subtype": "init", "session_id": sid})
    dur = float(os.environ.get("FALSO_DURA", "6"))
    if retomando:
        with open(os.path.join(pasta, "entregas", "ajuste.txt"), "w", encoding="utf-8") as f:
            f.write(pedido)
        sai({"type": "assistant", "message": {"content": [{"type": "text", "text": "Apliquei o ajuste pedido."}]}})
        time.sleep(1.0)
        fim = "RESULTADO: OK\nAjuste aplicado e site refeito para a cidade certa."
    else:
        sai({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"description": "Buscando no Google Maps"}}]}})
        time.sleep(1.0)
        sai({"type": "assistant", "message": {"content": [{"type": "text", "text": "MARCO: Achei 9 academias, 5 sem site."}]}})
        time.sleep(dur)
        os.makedirs(os.path.join(pasta, "entregas"), exist_ok=True)
        with open(os.path.join(pasta, "entregas", "site.html"), "w", encoding="utf-8") as f:
            f.write("<h1>Academia de teste</h1>")
        fim = "RESULTADO: OK\nSite pronto para a Academia Corpo e Mente e e-mail em rascunho."
    sai({"type": "assistant", "message": {"content": [{"type": "text", "text": fim}]}})
    sai({"type": "result", "result": fim, "is_error": False, "session_id": sid})


if "--input-format" in args:
    cerebro()
else:
    missao()
