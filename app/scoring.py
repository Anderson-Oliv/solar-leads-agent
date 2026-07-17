"""
SolarScore - Fase 1.

Usa apenas dados obtidos sem custo adicional: situacao cadastral, CNAE, porte
declarado / capital social, tempo de atividade, tipo (matriz/filial) e UF.

Fases seguintes (infraestrutura via satelite/Solar API, dados financeiros
pagos como Serasa, sinais de momento da empresa) entram em versoes futuras
deste modulo.
"""

import unicodedata
from datetime import date, datetime
from typing import Any, Dict, Optional


def _normalizar(texto: str) -> str:
    """minusculo e sem acentos, pra casar 'Hotéis'/'hotel' e 'Clínica'/'clinica'."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()

# Segmentos prioritarios do ICP, por trecho de descricao de CNAE (case-insensitive).
# Peso 1-5 conforme prioridade de consumo energetico definida no modelo de ICP.
SEGMENTOS_PRIORITARIOS = {
    "supermercado": 5,
    "hipermercado": 5,
    "padaria": 5,
    "panifica": 5,
    "farmac": 4,
    "drogaria": 4,
    "academia": 4,
    "metalurg": 5,
    "auto center": 4,
    "lava a jato": 4,
    "lava-rapido": 4,
    "lava rapido": 4,
    "clinica": 4,
    "hospit": 5,  # cobre "hospital" e o plural irregular "hospitais"
    "hote": 5,  # cobre "hotel" e o plural irregular "hoteis"
    "mote": 5,  # cobre "motel" e o plural irregular "moteis"
    "restaurante": 4,
    "igreja": 3,
    "organizacoes religiosas": 3,
    "escola": 4,
    "colegio": 4,
    "condominio": 4,
    "armazenamento": 5,
    "deposito": 4,
    "logistic": 5,
    "frigorifico": 5,
    "clube": 4,
    "textil": 3,
    "texteis": 3,  # plural irregular de "textil"
    "tecelagem": 3,
    "embalagen": 3,  # cobre singular e plural
    "fabrica": 4,  # catch-all industria/fabricacao - vertical mais forte na base atual de clientes
    "producao de": 3,
    "aluguel de imov": 3,  # dono de galpao/predio proprio, proxy de infraestrutura
    "ensino": 4,
    "educacao": 3,
    "combustiv": 5,  # posto de combustivel - top do benchmark de mercado
}

# UFs com alta incidencia solar / tarifa elevada, priorizadas no ICP.
UF_PRIORITARIAS = {"SP", "MG", "GO", "MT", "MS", "PR"}

# Pesos somam 100. Segmento carrega o maior peso pois hoje e o sinal mais
# rico disponivel de graca (nao ha leitura real de consumo em kWh nesta fase).
PESOS = {
    "segmento": 40,
    "porte_financeiro": 25,
    "tempo_empresa": 15,
    "localizacao": 10,
    "estrutura_societaria": 10,
}


def score_segmento(cnae_descricao: Optional[str]) -> float:
    """0-5 pela aderencia da descricao do CNAE aos segmentos prioritarios do ICP."""
    if not cnae_descricao:
        return 0
    texto = _normalizar(str(cnae_descricao))
    melhor = 0
    for chave, peso in SEGMENTOS_PRIORITARIOS.items():
        if _normalizar(chave) in texto:
            melhor = max(melhor, peso)
    return melhor


def score_porte_financeiro(capital_social: Optional[float], porte: Optional[str] = None) -> float:
    """0-5 pela combinacao de capital social e porte declarado (ME/EPP/Demais).

    Capital social ausente (dado nao disponivel na fonte) recebe nota neutra,
    diferente de capital social declarado como zero (sinal real de porte baixo).
    """
    if capital_social in (None, ""):
        return 2.5

    try:
        valor = float(capital_social)
    except (TypeError, ValueError):
        return 2.5

    if valor >= 1_000_000:
        pontos = 5
    elif valor >= 500_000:
        pontos = 4
    elif valor >= 100_000:
        pontos = 3
    elif valor >= 50_000:
        pontos = 2
    elif valor > 0:
        pontos = 1
    else:
        pontos = 0

    porte_norm = str(porte or "").strip().upper()
    if porte_norm in {"DEMAIS", "MEDIO", "MÉDIO", "GRANDE"}:
        pontos = min(5, pontos + 1)
    elif porte_norm == "MEI":
        pontos = max(0, pontos - 1)

    return min(pontos, 5)


def score_tempo_empresa(data_inicio_atividade: Optional[Any]) -> float:
    """0-5 pelo tempo de atividade. O ICP considera > 2 anos o piso ideal."""
    if not data_inicio_atividade:
        return 0
    try:
        if isinstance(data_inicio_atividade, str):
            inicio = datetime.strptime(data_inicio_atividade[:10], "%Y-%m-%d").date()
        elif isinstance(data_inicio_atividade, datetime):
            inicio = data_inicio_atividade.date()
        elif isinstance(data_inicio_atividade, date):
            inicio = data_inicio_atividade
        else:
            return 0
    except ValueError:
        return 0

    anos = (date.today() - inicio).days / 365.25
    if anos >= 10:
        return 5
    if anos >= 5:
        return 4
    if anos >= 2:
        return 3
    if anos >= 1:
        return 1
    return 0


def score_localizacao(uf: Optional[str]) -> float:
    """0-5: UFs com alta incidencia solar / tarifa elevada priorizadas no ICP."""
    if not uf:
        return 0
    return 5 if str(uf).strip().upper() in UF_PRIORITARIAS else 2


def score_estrutura_societaria(tipo: Optional[str]) -> float:
    """0-5: matriz pontua mais que filial (decisao de compra tende a vir da matriz)."""
    if not tipo:
        return 2
    return 5 if str(tipo).strip().upper() == "MATRIZ" else 2


def calcular_score(empresa: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula o SolarScore (0-100) de uma empresa - Fase 1.

    Aceita um dict com as chaves (todas opcionais, exceto que sem
    `situacao_cadastral` a empresa nao e desqualificada por esse criterio):
      - situacao_cadastral: str
      - cnae_descricao (ou descricao_cnae): str
      - capital_social: float
      - porte: str
      - data_inicio_atividade: str "YYYY-MM-DD" | date | datetime
      - uf (ou estado): str
      - tipo (ou tipo_empresa): "Matriz" | "Filial"
    """
    situacao = str(empresa.get("situacao_cadastral") or "").strip().lower()
    if situacao and situacao != "ativa":
        return {
            "score": 0,
            "classificacao": "🔴 Desqualificado (situação cadastral não ativa)",
            "detalhes": {},
        }

    cnae_desc = empresa.get("cnae_descricao") or empresa.get("descricao_cnae")
    uf = empresa.get("uf") or empresa.get("estado")
    tipo = empresa.get("tipo") or empresa.get("tipo_empresa")

    notas = {
        "segmento": score_segmento(cnae_desc),
        "porte_financeiro": score_porte_financeiro(empresa.get("capital_social"), empresa.get("porte")),
        "tempo_empresa": score_tempo_empresa(empresa.get("data_inicio_atividade")),
        "localizacao": score_localizacao(uf),
        "estrutura_societaria": score_estrutura_societaria(tipo),
    }

    score_total = sum((nota / 5) * PESOS[criterio] for criterio, nota in notas.items())
    score_total = round(score_total, 1)

    if score_total >= 80:
        classificacao = "🟢 Lead Quente"
    elif score_total >= 60:
        classificacao = "🟡 Lead Bom"
    elif score_total >= 40:
        classificacao = "🟠 Nutrição"
    else:
        classificacao = "🔴 Baixa prioridade"

    return {"score": score_total, "classificacao": classificacao, "detalhes": notas}


if __name__ == "__main__":
    exemplo = {
        "situacao_cadastral": "Ativa",
        "cnae_descricao": "Hotéis",
        "capital_social": 1_200_000,
        "porte": "DEMAIS",
        "data_inicio_atividade": "2015-03-10",
        "uf": "SP",
        "tipo": "Matriz",
    }
    print(calcular_score(exemplo))
