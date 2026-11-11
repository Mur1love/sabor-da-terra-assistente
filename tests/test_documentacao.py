import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_readme_tem_como_rodar():
    texto = (RAIZ / "README.md").read_text()
    assert "## Como rodar" in texto
    for comando in ["python -m scripts.smoke_llm", "streamlit run app.py", "pytest"]:
        assert comando in texto
    assert "LLM_MODO=fixture" in texto


def test_docs03_registra_limites_com_data():
    texto = (RAIZ / "docs" / "03-diretriz-arquitetura.md").read_text()
    assert "Limites confirmados no projeto" in texto
    # A data precisa estar NA subseção (âncora), senão o guard casa qualquer
    # outra data do arquivo (ex.: 19/11/2026) e nunca pega a remoção.
    secao = texto.split("Limites confirmados no projeto", 1)[1][:600]
    assert re.search(r"em \*{0,2}\d{2}/\d{2}/\d{4}\*{0,2}", secao)


def test_env_nao_e_rastreado_pelo_git():
    resultado = subprocess.run(
        ["git", "check-ignore", "-q", ".env"], cwd=RAIZ
    )
    assert resultado.returncode == 0


def test_historico_nao_tem_chave_gemini():
    saida = subprocess.run(
        ["git", "log", "-p", "--all"], cwd=RAIZ, capture_output=True, text=True
    ).stdout
    assert not re.search(r"AIza[0-9A-Za-z_-]{30,}", saida)
