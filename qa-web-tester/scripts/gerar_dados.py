#!/usr/bin/env python3
"""
Gerador de dados sintéticos para testes de QA.

Produz CPFs, CNPJs, cartões, telefones e CEPs válidos e inválidos, com o motivo
de cada invalidez explicitado — assim o relatório de teste consegue dizer
"rejeitou porque o dígito verificador está errado" em vez de só "rejeitou".

Nenhum dado aqui pertence a uma pessoa real: os números são gerados
aleatoriamente e validados apenas pelo algoritmo de dígito verificador.

Uso:
    python gerar_dados.py                    # texto legível
    python gerar_dados.py --formato json     # para consumo pelo runner
    python gerar_dados.py --quantidade 5     # mais amostras válidas
"""

import argparse
import json
import random
import sys

# Ver a nota em runner.py: sem isto o terminal do Windows quebra ao imprimir acentos.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


# ---------------------------------------------------------------- CPF

def calcular_dv_cpf(digitos):
    """Calcula um dígito verificador de CPF a partir dos dígitos anteriores."""
    peso = len(digitos) + 1
    soma = sum(d * (peso - i) for i, d in enumerate(digitos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def gerar_cpf_valido(com_mascara=True):
    base = [random.randint(0, 9) for _ in range(9)]
    # Evita gerar acidentalmente um CPF de dígitos repetidos, que é inválido.
    while len(set(base)) == 1:
        base = [random.randint(0, 9) for _ in range(9)]
    base.append(calcular_dv_cpf(base))
    base.append(calcular_dv_cpf(base))
    numeros = "".join(map(str, base))
    if com_mascara:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    return numeros


def validar_cpf(valor):
    """Referência de verdade: use para conferir o que o sistema testado decidiu."""
    numeros = [int(c) for c in valor if c.isdigit()]
    if len(numeros) != 11:
        return False
    if len(set(numeros)) == 1:
        return False
    if calcular_dv_cpf(numeros[:9]) != numeros[9]:
        return False
    return calcular_dv_cpf(numeros[:10]) == numeros[10]


def cpfs_invalidos():
    valido = gerar_cpf_valido(com_mascara=False)
    # Altera o último dígito para quebrar o DV sem mudar mais nada.
    dv_errado = valido[:10] + str((int(valido[10]) + 1) % 10)
    return [
        {"valor": "", "motivo": "campo vazio"},
        {"valor": "   ", "motivo": "apenas espaços em branco"},
        {"valor": "111.111.111-11", "motivo": "todos os dígitos iguais"},
        {"valor": "000.000.000-00", "motivo": "todos os dígitos iguais (zeros)"},
        {"valor": f"{dv_errado[:3]}.{dv_errado[3:6]}.{dv_errado[6:9]}-{dv_errado[9:]}",
         "motivo": "dígito verificador incorreto"},
        {"valor": valido[:9], "motivo": "menos de 11 dígitos"},
        {"valor": valido + "9", "motivo": "mais de 11 dígitos"},
        {"valor": "abc.def.ghi-jk", "motivo": "letras no lugar de números"},
        {"valor": "529@982#247$26", "motivo": "separadores inválidos (@ # $) e DV incorreto"},
    ]


# ---------------------------------------------------------------- CNPJ

PESOS_CNPJ_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
PESOS_CNPJ_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def calcular_dv_cnpj(digitos, pesos):
    soma = sum(d * p for d, p in zip(digitos, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def gerar_cnpj_valido(com_mascara=True):
    base = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    base.append(calcular_dv_cnpj(base, PESOS_CNPJ_1))
    base.append(calcular_dv_cnpj(base, PESOS_CNPJ_2))
    n = "".join(map(str, base))
    if com_mascara:
        return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"
    return n


def validar_cnpj(valor):
    numeros = [int(c) for c in valor if c.isdigit()]
    if len(numeros) != 14 or len(set(numeros)) == 1:
        return False
    if calcular_dv_cnpj(numeros[:12], PESOS_CNPJ_1) != numeros[12]:
        return False
    return calcular_dv_cnpj(numeros[:13], PESOS_CNPJ_2) == numeros[13]


def cnpjs_invalidos():
    valido = gerar_cnpj_valido(com_mascara=False)
    dv_errado = valido[:13] + str((int(valido[13]) + 1) % 10)
    return [
        {"valor": "", "motivo": "campo vazio"},
        {"valor": "11.111.111/1111-11", "motivo": "todos os dígitos iguais"},
        {"valor": dv_errado, "motivo": "dígito verificador incorreto"},
        {"valor": valido[:10], "motivo": "menos de 14 dígitos"},
        {"valor": "ab.cde.fgh/ijkl-mn", "motivo": "letras no lugar de números"},
    ]


# ---------------------------------------------------------------- Cartão

def passa_luhn(numero):
    digitos = [int(c) for c in numero if c.isdigit()][::-1]
    total = 0
    for i, d in enumerate(digitos):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def gerar_cartao(prefixo, comprimento):
    corpo = [int(c) for c in prefixo]
    corpo += [random.randint(0, 9) for _ in range(comprimento - len(prefixo) - 1)]
    # Descobre o último dígito que faz a soma de Luhn fechar em zero.
    for dv in range(10):
        if passa_luhn("".join(map(str, corpo + [dv]))):
            return "".join(map(str, corpo + [dv]))
    return None


def cartoes():
    return {
        "validos_luhn": [
            {"bandeira": "Visa", "numero": gerar_cartao("4", 16), "cvv": "123"},
            {"bandeira": "Mastercard", "numero": gerar_cartao("55", 16), "cvv": "123"},
            {"bandeira": "Amex", "numero": gerar_cartao("37", 15), "cvv": "1234"},
        ],
        "invalidos": [
            {"valor": "4111 1111 1111 1112", "motivo": "falha no algoritmo de Luhn"},
            {"valor": "1234", "motivo": "número curto demais"},
            {"valor": "", "motivo": "campo vazio"},
            {"valor": "abcd efgh ijkl mnop", "motivo": "letras"},
        ],
        "validade_invalida": [
            {"valor": "01/20", "motivo": "validade no passado"},
            {"valor": "13/30", "motivo": "mês inexistente"},
            {"valor": "00/30", "motivo": "mês zero"},
            {"valor": "", "motivo": "campo vazio"},
        ],
        "observacao": (
            "Estes números passam no Luhn mas NÃO são cartões de sandbox. "
            "Para testar aprovação/recusa real, use os cartões de teste do "
            "gateway do projeto (Stripe, Pagar.me, Mercado Pago, Cielo)."
        ),
    }


# ---------------------------------------------------------------- Outros

def outros_dados():
    return {
        "email": {
            "validos": ["qa.teste@exemplo.com.br", "TESTE@EXEMPLO.COM"],
            "invalidos": [
                {"valor": "", "motivo": "vazio"},
                {"valor": "semarroba.com", "motivo": "sem @"},
                {"valor": "teste@", "motivo": "sem domínio"},
                {"valor": "teste@exemplo", "motivo": "sem TLD"},
                {"valor": "tes te@exemplo.com", "motivo": "espaço no meio"},
            ],
        },
        "telefone": {
            "validos": ["(61) 99999-9999", "(11) 3333-4444"],
            "invalidos": [
                {"valor": "(00) 99999-9999", "motivo": "DDD inexistente"},
                {"valor": "9999-9999", "motivo": "sem DDD"},
                {"valor": "(61) 9999", "motivo": "dígitos insuficientes"},
            ],
        },
        "cep": {
            "validos": ["70040-010", "01310-100"],
            "invalidos": [
                {"valor": "99999-999", "motivo": "formato válido mas inexistente"},
                {"valor": "1234", "motivo": "incompleto"},
                {"valor": "abcde-fgh", "motivo": "letras"},
            ],
        },
        "sanitizacao": [
            {"valor": "<script>alert(1)</script>", "motivo": "deve ser exibido como texto, sem executar"},
            {"valor": "' OR '1'='1", "motivo": "não deve gerar erro de banco na tela"},
            {"valor": "José 🎉 Ção", "motivo": "acentos e emoji devem persistir corretamente"},
            {"valor": "A" * 5000, "motivo": "string longa não deve causar erro 500"},
        ],
    }


def montar(quantidade):
    return {
        "cpf": {
            "validos_com_mascara": [gerar_cpf_valido(True) for _ in range(quantidade)],
            "validos_sem_mascara": [gerar_cpf_valido(False) for _ in range(quantidade)],
            "invalidos": cpfs_invalidos(),
        },
        "cnpj": {
            "validos": [gerar_cnpj_valido(True) for _ in range(quantidade)],
            "invalidos": cnpjs_invalidos(),
        },
        "cartao": cartoes(),
        **outros_dados(),
    }


def imprimir_legivel(dados, prefixo=""):
    for chave, valor in dados.items():
        if isinstance(valor, dict):
            print(f"\n{prefixo}[{chave.upper()}]")
            imprimir_legivel(valor, prefixo + "  ")
        elif isinstance(valor, list):
            print(f"{prefixo}{chave}:")
            for item in valor:
                if isinstance(item, dict):
                    campos = " | ".join(f"{k}={v}" for k, v in item.items())
                    print(f"{prefixo}  - {campos[:120]}")
                else:
                    print(f"{prefixo}  - {item}")
        else:
            print(f"{prefixo}{chave}: {valor}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Gera dados sintéticos para QA")
    p.add_argument("--formato", choices=["texto", "json"], default="texto")
    p.add_argument("--quantidade", type=int, default=3,
                   help="quantas amostras válidas gerar por documento")
    p.add_argument("--seed", type=int, help="fixa a aleatoriedade para reproduzir uma execução")
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    dados = montar(args.quantidade)

    if args.formato == "json":
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    else:
        imprimir_legivel(dados)
