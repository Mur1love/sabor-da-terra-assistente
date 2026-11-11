from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_smoke_usa_os_tres_papeis():
    texto = (RAIZ / "scripts" / "smoke_llm.py").read_text()
    assert "Papel.TRIAGEM" in texto
    assert "Papel.RESPOSTA" in texto
    # O embedding entra por embedar(), que resolve Papel.EMBEDDING no cliente.
    assert "embedar(" in texto
    assert "load_dotenv()" in texto


def test_app_streamlit_tem_titulo():
    texto = (RAIZ / "app.py").read_text()
    assert "st.set_page_config(" in texto
    assert "Sabor da Terra — Assistente" in texto
