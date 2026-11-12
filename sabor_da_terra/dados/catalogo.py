"""Liga o nome que alguém escreveu ao produto da cooperativa.

O mesmo produto aparece como "goiaba", "goiaba paluma" e "goiaba paluma extra"
nos arquivos. O produto base é a linha da sazonalidade; a variante é a linha da
tabela de preços.

A busca só aceita correspondência segura: nome, plural ou apelido. Se o termo
apenas se parece com um produto ("melão" e melado), volta uma sugestão sem
dados, e o assistente confirma com a pessoa.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from sabor_da_terra.dados.normalizacao import chave

# Variante da tabela de preços → produto base (o resto tem o mesmo nome nos dois).
VARIANTE_PARA_BASE: dict[str, str] = {
    "goiaba paluma extra": "goiaba paluma",
    "goiaba paluma especial": "goiaba paluma",
    "tomate santa cruz": "tomate",
    "pimentão verde": "pimentão",
    "pimentão colorido": "pimentão",
}

# Jeitos comuns de chamar um produto base (chave sem acento → nome do base).
# Só entra aqui o que é o mesmo produto, nunca um parecido.
APELIDOS: dict[str, str] = {
    "goiaba": "goiaba paluma",
    "manga": "manga tommy",
    "banana": "banana prata",
    "coco": "coco verde",
    "tapioca": "tapioca/goma",
    "goma": "tapioca/goma",
    "ovo": "ovos caipira",
    "ovos": "ovos caipira",
    "ovo caipira": "ovos caipira",
    "frango": "frango caipira",
    "jandaira": "mel de jandaíra",
    "mel de abelha jandaira": "mel de jandaíra",
    "mel jandaira": "mel de jandaíra",
    "mandioca": "macaxeira",
    "aipim": "macaxeira",
    "queijo de coalho": "queijo coalho",
    "geleia": "geleia de frutas",
    "farinha": "farinha de mandioca",
    "iogurte": "iogurte natural",
    "cera": "cera de abelha",
}


@dataclass(frozen=True)
class Resolucao:
    termo: str
    base: str | None = None  
    variante: str | None = None  
    candidatos: list[str] = field(default_factory=list)  
    ambiguo: bool = False  

    # Diz se o termo virou um produto com segurança.
    @property
    def encontrado(self) -> bool:
        return self.base is not None

    # Monta a frase que o assistente repassa quando não achou o produto.
    def aviso(self) -> str | None:
        if self.encontrado:
            return None
        if self.ambiguo:
            return f"'{self.termo}' pode ser: {', '.join(self.candidatos)}. Pergunte qual."
        if self.candidatos:
            return (
                f"Não há produto chamado '{self.termo}' no catálogo. "
                f"O mais próximo é {', '.join(self.candidatos)}: confirme com a pessoa antes de usar."
            )
        return f"Nenhum produto do catálogo corresponde a '{self.termo}'."


class Catalogo:
    # Agrupa as linhas de preço por produto base e prepara as buscas.
    def __init__(self, nomes_preco: list[str], nomes_sazonalidade: list[str]):
        self._variantes: dict[str, list[str]] = {}
        for nome in nomes_preco:
            base = VARIANTE_PARA_BASE.get(nome, nome)
            self._variantes.setdefault(base, []).append(nome)
        for nome in nomes_sazonalidade:
            self._variantes.setdefault(nome, [])

        self._base_por_chave = {chave(base): base for base in self._variantes}
        self._variante_por_chave = {
            chave(v): v for vs in self._variantes.values() for v in vs
        }
        self._apelidos = {k: v for k, v in APELIDOS.items() if v in self._variantes}

    # Lista os produtos base em ordem alfabética.
    @property
    def bases(self) -> list[str]:
        return sorted(self._variantes)

    # Lista as linhas de preço de um produto base.
    def variantes(self, base: str) -> list[str]:
        return list(self._variantes.get(base, []))

    # Diz a qual produto base uma linha de preço pertence.
    def base_da_variante(self, variante: str) -> str:
        return VARIANTE_PARA_BASE.get(variante, variante)

    # Transforma o que a pessoa escreveu em produto, opções ou sugestão.
    def resolver(self, termo: str) -> Resolucao:
        k = chave(termo)
        if not k:
            return Resolucao(termo=termo)

        seguro = self._resolver_seguro(k)
        if seguro:
            base, variante = seguro
            return Resolucao(termo=termo, base=base, variante=variante)

        palavras = set(k.split())
        parciais = sorted(
            {
                self.base_da_variante(nome)
                for chave_nome, nome in {**self._base_por_chave, **self._variante_por_chave}.items()
                if palavras <= set(chave_nome.split())
            }
        )
        if parciais:
            return Resolucao(termo=termo, candidatos=parciais, ambiguo=len(parciais) > 1)

        todas = {**self._base_por_chave, **self._variante_por_chave, **self._apelidos}
        parecidas = difflib.get_close_matches(k, list(todas), n=3, cutoff=0.8)
        return Resolucao(termo=termo, candidatos=sorted({self.base_da_variante(todas[p]) for p in parecidas}))

    # Tenta as formas seguras do termo e para na primeira que bate.
    def _resolver_seguro(self, k: str) -> tuple[str, str | None] | None:
        for tentativa in self._formas(k):
            achado = self._resolver_exato(tentativa)
            if achado:
                return achado
        return None

    # Gera as variações aceitas do termo: original, singular e apelido expandido.
    def _formas(self, k: str) -> list[str]:
        formas = [k]
        if k.endswith("s"):
            formas.append(k[:-1])
        for apelido in sorted(self._apelidos, key=len, reverse=True):
            if k.startswith(apelido + " "):
                formas.append(chave(self._apelidos[apelido]) + k[len(apelido):])
                break
        return formas

    # Procura o termo como produto base, linha de preço ou apelido.
    def _resolver_exato(self, k: str) -> tuple[str, str | None] | None:
        if k in self._base_por_chave:
            return self._base_por_chave[k], None
        if k in self._variante_por_chave:
            variante = self._variante_por_chave[k]
            return self.base_da_variante(variante), variante
        if k in self._apelidos:
            return self._apelidos[k], None
        return None
