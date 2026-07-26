"""
Secretário IA Empresarial.

O pacote contém configuração, modelo, roteamento seletivo,
ferramentas e execução do agente.
"""

from agente.configuracao import (
    ConfiguracaoAgente,
    carregar_configuracao,
)
from agente.executor import (
    conversar,
    criar_agente,
    executar_agente,
    extrair_resposta_final,
    visualizar_roteamento,
)
from agente.modelo import criar_modelo
from agente.prompt import (
    PROMPT_SECRETARIO_EMPRESARIAL,
)
from agente.roteador import (
    LIMITE_FERRAMENTAS_POR_REQUISICAO,
    ResultadoRoteamento,
    diagnosticar_roteamento,
    rotear_ferramentas,
    selecionar_ferramentas,
)


__all__ = [
    "ConfiguracaoAgente",
    "LIMITE_FERRAMENTAS_POR_REQUISICAO",
    "PROMPT_SECRETARIO_EMPRESARIAL",
    "ResultadoRoteamento",
    "carregar_configuracao",
    "conversar",
    "criar_agente",
    "criar_modelo",
    "diagnosticar_roteamento",
    "executar_agente",
    "extrair_resposta_final",
    "rotear_ferramentas",
    "selecionar_ferramentas",
    "visualizar_roteamento",
]