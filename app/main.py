"""App web FastAPI: portal R$ Transparência (design system aplicado)."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import agenda
from . import ceap
from . import queries as Q
from . import ui
from .analysis import llm, summaries
from .config import ADSENSE_CLIENT, ADSENSE_SLOT_ARTIGO, ADSENSE_SLOT_FEED, SUBSIDIO_MENSAL
from .db import init_db

BASE = Path(__file__).resolve().parent
app = FastAPI(title="R$ Transparência")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

# Helpers do design disponíveis em todos os templates
templates.env.globals.update(
    initials=ui.initials,
    party_color=ui.party_color,
    avatar_bg=ui.avatar_bg,
    avatar_fg=ui.avatar_fg,
    vote_kind=ui.vote_kind,
    vote_label=ui.VOTE_LABEL,
    vote_icon=ui.VOTE_ICON,
    kind_votacao=Q.kind_votacao,
    subsidio_mensal=SUBSIDIO_MENSAL,
    adsense_client=ADSENSE_CLIENT,
    adsense_slot_feed=ADSENSE_SLOT_FEED,
    adsense_slot_artigo=ADSENSE_SLOT_ARTIGO,
    og_base=__import__("os").getenv("PUBLIC_URL", "https://real-transparencia-production.up.railway.app").rstrip("/"),
)
templates.env.filters["brl"] = ui.brl
templates.env.filters["brlf"] = ui.brl_full
templates.env.filters["num"] = ui.num


@app.on_event("startup")
def _startup() -> None:
    init_db()


def render(request: Request, template: str, active: str = "", **ctx) -> HTMLResponse:
    ctx.update(active=active, grok_ok=llm.disponivel())
    return templates.TemplateResponse(request, template, ctx)


# ----------------------------------------------------------- LANDING / FEED
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    grupos = Q.feed_grouped(6)
    # destaque: primeira votação decidida no plenário (cai pro 1º grupo se não houver)
    destaque = next((g for g in grupos
                     if g["kind"] in ("aprovado", "rejeitado") and "PLEN" in (g["sigla_orgao"] or "")), None)
    if destaque is None and grupos:
        destaque = grupos[0]
    resto = [g for g in grupos if g is not destaque][:3]
    # custo mensal real (escala humana): salário fixo + teto médio de cota
    cota_media = round(sum(ceap.CEAP_MENSAL.values()) / len(ceap.CEAP_MENSAL))
    custo = dict(
        salario=SUBSIDIO_MENSAL, cota_teto=cota_media,
        por_dep=SUBSIDIO_MENSAL + cota_media,
        total_mes=(SUBSIDIO_MENSAL + cota_media) * 513,
    )
    return render(request, "landing.html", active="",
                  stats=Q.home_stats(), feed=resto, destaque=destaque,
                  ufs=Q.filtros_disponiveis()["ufs"], custo=custo)


@app.post("/api/sugestao", response_class=HTMLResponse)
async def api_sugestao(request: Request):
    import urllib.parse as _up
    raw = (await request.body()).decode("utf-8", "ignore")
    data = _up.parse_qs(raw)
    texto = (data.get("texto", [""])[0] or "").strip()
    pagina = data.get("pagina", [""])[0] or ""
    if not texto:
        return HTMLResponse('<p class="sug-msg">Escreva algo antes de enviar 🙂</p>')
    Q.salvar_sugestao(texto, pagina)
    return HTMLResponse('<div class="sug-done"><i data-lucide="check-circle"></i>'
                        '<p>Valeu! Sua sugestão foi enviada, anônima.</p></div>'
                        '<script>window.lucide&&lucide.createIcons();</script>')


@app.get("/sugestoes", response_class=HTMLResponse)
def sugestoes(request: Request):
    return render(request, "sugestoes.html", active="", lista=Q.listar_sugestoes())


@app.get("/buscar", response_class=HTMLResponse)
def buscar(request: Request, q: str = "", busca: str = ""):
    """Autocomplete dinâmico (HTMX): partidos + deputados que casam com o termo."""
    q = (q or busca or "").strip()
    if len(q) < 1:
        return HTMLResponse("")
    partidos = [p for p in Q.partidos_list() if p and q.upper() in p.upper()][:6]
    deps = Q.buscar_deputados(q, limit=8)
    return render(request, "_busca_result.html", q=q, partidos=partidos, deps=deps)


@app.get("/agora", response_class=HTMLResponse)
def feed(request: Request):
    return render(request, "feed.html", active="feed",
                  grupos=Q.feed_grouped(14), vigiados=Q.mais_vigiados(5),
                  ausentes=Q.ausentes_recentes(100, 6), gastoes=Q.gastoes_recentes(3, 6),
                  pauta=agenda.proximas_votacoes())


# ---------------------------------------------------------------- DEPUTADOS
@app.get("/deputados", response_class=HTMLResponse)
def lista_deputados(request: Request, uf: str | None = None, partido: str | None = None, busca: str | None = None):
    return render(request, "deputados.html", active="deputy",
                  deputados=Q.list_deputados(uf, partido, busca),
                  filtros=Q.filtros_disponiveis(), uf=uf, partido=partido, busca=busca or "")


@app.get("/deputados/{dep_id}", response_class=HTMLResponse)
def deputado(request: Request, dep_id: int):
    dep = Q.get_deputado(dep_id)
    if not dep:
        return HTMLResponse("Deputado não encontrado", status_code=404)
    presenca = Q.deputado_presenca(dep_id)
    dep["presence"] = presenca["pct"] if presenca else None
    ano = Q.ano_corrente()
    salario = dict(
        mensal=SUBSIDIO_MENSAL,
        meses_ano=ui.meses_decorridos_ano(ano),
        recebido_ano=SUBSIDIO_MENSAL * ui.meses_decorridos_ano(ano),
        meses_mandato=ui.meses_no_mandato(),
        total_mandato=SUBSIDIO_MENSAL * ui.meses_no_mandato(),
    )
    trabalho = dict(
        ano=ano,
        dias_presenca=Q.deputado_dias_presenca(dep_id, ano),
        dias_uteis=ui.dias_uteis_ano(ano),
    )
    fin = Q.deputado_resumo_financeiro(dep_id, ano)
    lim = ceap.limite_anual(dep.get("sigla_uf"))
    cota = dict(
        limite_anual=lim, limite_mensal=ceap.limite_mensal(dep.get("sigla_uf")),
        pct=round(100 * fin["total"] / lim, 1) if lim else None,
    )
    return render(request, "deputado.html", active="deputy",
                  dep=dep, stats=Q.deputado_stats(dep_id, ano), presenca=presenca,
                  financeiro=fin, cota=cota, salario=salario, trabalho=trabalho,
                  serie=Q.deputado_serie_anual(dep_id),
                  votos=Q.deputado_votos_agrupado(dep_id), eleicao=Q.deputado_eleicao(dep_id))


@app.get("/deputados/{dep_id}/gastos", response_class=HTMLResponse)
def deputado_gastos(request: Request, dep_id: int, cat: str | None = None,
                    ano: int | None = None, mes: int | None = None):
    dep = Q.get_deputado(dep_id)
    if not dep:
        return HTMLResponse("Deputado não encontrado", status_code=404)
    ano = ano or Q.ano_corrente()
    fin = Q.deputado_resumo_financeiro(dep_id, ano)
    limite = ceap.limite_anual(dep.get("sigla_uf"))
    pct_cota = round(100 * fin["total"] / limite, 1) if limite else None
    recibos = Q.deputado_recibos(dep_id, limit=(80 if (cat or mes) else 15), categoria=cat, ano=ano, mes=mes)
    return render(request, "deputado_gastos.html", active="gastos",
                  dep=dep, financeiro=fin, ano=ano, anos=Q.anos_despesa(), cat=cat, mes=mes,
                  limite_mensal=ceap.limite_mensal(dep.get("sigla_uf")), limite_anual=limite, pct_cota=pct_cota,
                  mensal=Q.deputado_gasto_mensal(dep_id, ano), recibos=recibos)


# ----------------------------------------------------------------- VOTAÇÕES
@app.get("/votacoes", response_class=HTMLResponse)
def votacoes(request: Request, ano: int | None = None, mes: int | None = None):
    anos = Q.anos_despesa()
    return render(request, "votacoes.html", active="votacao",
                  feed=Q.feed_items(60, ano=ano, mes=mes), anos=anos, ano=ano, mes=mes)


@app.get("/votacoes/{vid}", response_class=HTMLResponse)
def votacao(request: Request, vid: str):
    v = Q.get_votacao(vid)
    if not v:
        return HTMLResponse("Votação não encontrada", status_code=404)
    sim = v.get("votos_sim") or 0
    nao = v.get("votos_nao") or 0
    outros = v.get("votos_outros") or 0
    v["titulo"] = v.get("titulo_ia") or v.get("ementa") or v.get("descricao") or ("Votação " + vid)
    votos_list = Q.votacao_votos(vid)
    from collections import Counter
    kinds = Counter(ui.vote_kind(x["voto"]) for x in votos_list)
    chip = {"all": len(votos_list), "sim": kinds["sim"], "nao": kinds["nao"],
            "outros": kinds["abs"] + kinds["aus"]}
    return render(request, "votacao.html", active="votacao",
                  v=v, kind=Q.kind_resultado(v["aprovacao"], sim, nao), sim=sim, nao=nao, outros=outros,
                  chip=chip, partidos=Q.votacao_partidos(vid), votos=votos_list,
                  texto=Q.proposicao_link(v.get("objeto")))


@app.get("/partido/{sigla}/projetos", response_class=HTMLResponse)
def partido_projetos(request: Request, sigla: str, desfecho: str = "lei", ano: int | None = None):
    if desfecho not in ("lei", "arquivado", "todos"):
        desfecho = "lei"
    ano = ano or Q.ano_corrente()
    anos = Q.anos_mandato(ano)
    counts = Q.producao_por_partido(anos).get(sigla.upper(), {"apresentados": 0, "lei": 0, "arquivado": 0})
    return render(request, "partido_projetos.html", active="raiox",
                  sigla=sigla.upper(), desfecho=desfecho, ano=ano, anos=anos,
                  lista=Q.partido_projetos(sigla.upper(), anos, desfecho), counts=counts)


# --------------------------------------------------------- GASTOS / OUTRAS
@app.get("/gastos", response_class=HTMLResponse)
def gastos(request: Request, ano: int | None = None, mes: int | None = None):
    # Gastos = só o financeiro (panorama de despesas da cota)
    anos = Q.anos_despesa()
    ano = ano or (anos[0] if anos else 2024)
    return render(request, "gastos.html", active="gastos", anos=anos, ano=ano, mes=mes,
                  kpis=Q.relatorio_kpis(ano, mes), mensal=Q.gasto_mensal_global(ano),
                  categorias=Q.categorias_agg(ano, mes), maiores=Q.maiores_notas(ano, 12, mes=mes),
                  partidos=Q.gasto_por_partido(ano, mes), ranking=Q.ranking_gastos_deputados(20, ano=ano, mes=mes),
                  overview=Q.gastos_overview(ano), fornecedores=Q.top_fornecedores(ano, 25),
                  exclusivos=Q.fornecedores_exclusivos(ano), repetidos=Q.valores_repetidos(ano),
                  pf=Q.pessoa_fisica_top(ano))


@app.get("/fornecedor", response_class=HTMLResponse)
def fornecedor(request: Request, nome: str, ano: int | None = None, dep: int | None = None):
    if not nome:
        return RedirectResponse("/gastos")
    return render(request, "fornecedor.html", active="gastos", ano=ano,
                  d=Q.fornecedor_detalhe(nome, ano, dep))


@app.get("/relatorio", response_class=HTMLResponse)
def relatorio(request: Request, escopo: str = "geral", alvo: str | None = None, ano: int | None = None):
    anos = Q.anos_despesa()
    ano = ano or (anos[0] if anos else 2024)
    if escopo not in ("geral", "partido", "deputado") or (escopo != "geral" and not alvo):
        escopo, alvo = "geral", None
    # escopo=deputado exige alvo numérico (id); qualquer coisa inválida volta ao geral
    if escopo == "deputado" and not (alvo or "").isdigit():
        escopo, alvo = "geral", None
    d = Q.raiox_data(escopo, alvo, ano)
    return render(request, "relatorio.html", active="raiox", anos=anos, ano=ano,
                  escopo=escopo, alvo=alvo, d=d,
                  partidos_gasto=Q.gasto_por_partido(ano), ranking=Q.ranking_gastos_deputados(15, ano=ano),
                  lista_partidos=Q.partidos_list(), lista_deputados=Q.deputados_min())


@app.get("/relatorio/partido/{sigla}", response_class=HTMLResponse)
def relatorio_partido(request: Request, sigla: str, ano: int | None = None, mes: int | None = None):
    anos = Q.anos_despesa()
    ano = ano or (anos[0] if anos else 2024)
    return render(request, "relatorio_partido.html", active="gastos", anos=anos, ano=ano, mes=mes, sigla=sigla,
                  kpis=Q.partido_kpis(sigla, ano, mes), mensal=Q.partido_mensal(sigla, ano),
                  deputados=Q.partido_top_deputados(sigla, ano, mes), categorias=Q.partido_categorias(sigla, ano, mes))


@app.get("/relatorio/categoria/{cat}", response_class=HTMLResponse)
def relatorio_categoria(request: Request, cat: str, ano: int | None = None):
    anos = Q.anos_despesa()
    ano = ano or (anos[0] if anos else 2024)
    return render(request, "relatorio_categoria.html", active="gastos", anos=anos, ano=ano, cat=cat,
                  kpis=Q.categoria_kpis(cat, ano), mensal=Q.categoria_mensal(cat, ano),
                  fornecedores=Q.categoria_fornecedores(cat, ano), notas=Q.categoria_notas(cat, ano),
                  variacao=Q.variacao_preco_categoria(cat, ano))


@app.get("/fornecedores", response_class=HTMLResponse)
def fornecedores(request: Request):
    return render(request, "fornecedores.html", active="gastos", fornecedores=Q.ranking_fornecedores(40))


@app.get("/eleicoes", response_class=HTMLResponse)
def eleicoes(request: Request, ano: int | None = None):
    anos = Q.anos_eleicao()
    ano = ano or (anos[0] if anos else None)
    eleitos = Q.eleicao_eleitos(ano) if ano else []
    return render(request, "eleicoes.html", active="", anos=anos, ano=ano, eleitos=eleitos)


@app.get("/ads.txt", response_class=PlainTextResponse)
def ads_txt():
    """ads.txt do AdSense (autoriza o Google a vender o inventário do site)."""
    if not ADSENSE_CLIENT:
        return PlainTextResponse("", status_code=404)
    pub = ADSENSE_CLIENT.replace("ca-", "", 1)  # ca-pub-XXXX -> pub-XXXX
    return PlainTextResponse(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")


@app.get("/componentes", response_class=HTMLResponse)
def componentes(request: Request):
    return render(request, "componentes.html", active="")


# ----------------------------------------- Resumos sob demanda (Grok, HTMX)
@app.post("/api/resumo/votacao/{vid}", response_class=HTMLResponse)
def resumo_votacao(vid: str):
    v = Q.get_votacao(vid)
    if not v:
        return HTMLResponse("", status_code=404)
    try:
        texto = summaries.resumo_votacao(v, Q.votacao_placar(vid), Q.votacao_orientacoes(vid))
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(_erro_html(exc))
    return HTMLResponse(_resumo_html(texto))


@app.post("/api/resumo/deputado/{dep_id}", response_class=HTMLResponse)
def resumo_deputado(dep_id: int):
    dep = Q.get_deputado(dep_id)
    if not dep:
        return HTMLResponse("", status_code=404)
    try:
        ano = Q.ano_corrente()
        texto = summaries.resumo_deputado(
            dep, Q.deputado_resumo_financeiro(dep_id, ano), Q.deputado_presenca(dep_id),
            Q.deputado_eleicao(dep_id), Q.deputado_stats(dep_id, ano)
        )
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(_erro_html(exc))
    return HTMLResponse(_resumo_html(texto))


def _erro_html(exc: Exception) -> str:
    msg = str(exc).lower()
    if "credit" in msg or "permission" in msg:
        aviso = "A conta de IA ainda não tem créditos. Configure a chave/billing para gerar os resumos."
    elif "429" in msg or "quota" in msg or "rate" in msg:
        aviso = "Análise sendo preparada (limite gratuito momentâneo). Atualize em instantes, ela fica salva quando gerada."
    else:
        aviso = "Não foi possível gerar o resumo agora. Tente de novo em instantes."
    return f'<p class="muted">{aviso}</p>'


def _resumo_html(texto: str | None) -> str:
    if not texto:
        return '<p class="muted">Resumo indisponível: configure a variável <code>XAI_API_KEY</code>.</p>'
    import html as _html

    blocos = []
    for linha in (l.strip() for l in texto.splitlines()):
        if not linha:
            continue
        if ":" in linha and len(linha.split(":", 1)[0]) <= 28:
            rotulo, resto = linha.split(":", 1)
            blocos.append(
                f'<p class="t-body" style="margin:0 0 8px">'
                f'<strong style="color:var(--green-800)">{_html.escape(rotulo)}:</strong>'
                f'{_html.escape(resto)}</p>'
            )
        else:
            blocos.append(f'<p class="t-body" style="margin:0 0 8px">{_html.escape(linha)}</p>')
    corpo = "".join(blocos)
    return f'{corpo}<p class="muted" style="font-size:12px;margin-top:8px">Resumo gerado por IA (Grok) a partir dos dados oficiais.</p>'
