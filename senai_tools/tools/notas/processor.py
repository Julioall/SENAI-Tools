from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Sequence

import pandas as pd
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def extrair_nome_uc(nome_arquivo: str) -> str:
    """
    Retorna somente o nome da UC (sem código e sem o sufixo 'Notas').
    Exemplo: '1035754 - Banco de Dados Notas.xlsx' -> 'Banco de Dados'
    """
    base = Path(nome_arquivo).stem
    if base.endswith(" Notas"):
        base = base[:-6]
    if " - " in base:
        return base.split(" - ", 1)[1]
    return base


def formatar_worksheet(ws) -> None:
    """
    Formatação básica:
    - Cabeçalho em negrito, fundo cinza claro, centralizado
    - Bordas em toda a tabela
    - Largura de colunas ajustada
    - Formatação condicional em 'Total do Curso'
    """
    max_row = ws.max_row
    max_col = ws.max_column

    # Estilos básicos
    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="DDDDDD")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_side = Side(border_style="thin", color="000000")
    border = Border(top=thin_side, left=thin_side, right=thin_side, bottom=thin_side)

    # Cabeçalho
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border

    # Bordas e alinhamento das linhas de dados
    for row in ws.iter_rows(min_row=2, max_row=max_row, max_col=max_col):
        for cell in row:
            cell.border = border
            if isinstance(cell.value, str):
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")

    # Ajuste de largura de colunas
    for col_idx in range(1, max_col + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row in range(1, max_row + 1):
            cell = ws[f"{col_letter}{row}"]
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))
        ws.column_dimensions[col_letter].width = max_len + 2

    # Formatação condicional para 'Total do Curso'
    total_col_idx = None
    for cell in ws[1]:
        if str(cell.value).strip() == "Total do Curso":
            total_col_idx = cell.column
            break

    if total_col_idx and max_row >= 2:
        col_letter = get_column_letter(total_col_idx)
        cell_range = f"{col_letter}2:{col_letter}{max_row}"

        regra_verde = CellIsRule(
            operator="greaterThanOrEqual",
            formula=["60"],
            stopIfTrue=False,
            fill=PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        )
        regra_amarela = CellIsRule(
            operator="between",
            formula=["40", "59"],
            stopIfTrue=False,
            fill=PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        )
        regra_vermelha = CellIsRule(
            operator="lessThan",
            formula=["40"],
            stopIfTrue=False,
            fill=PatternFill(start_color="F2DCDB", end_color="F2DCDB", fill_type="solid"),
        )

        ws.conditional_formatting.add(cell_range, regra_verde)
        ws.conditional_formatting.add(cell_range, regra_amarela)
        ws.conditional_formatting.add(cell_range, regra_vermelha)


def processar_arquivos(
    lista_arquivos: Sequence[str],
    arquivo_saida: str,
    *,
    dividir_por_uc: bool = False,
    manter_nome_original: bool = False,
    log_callback: Callable[[str], None] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """
    Consolida os relatórios em um único arquivo Excel.

    Args:
        lista_arquivos: caminhos dos relatórios .xlsx/.ods.
        arquivo_saida: caminho completo do arquivo consolidado.
        dividir_por_uc: cria uma aba por UC quando True.
        manter_nome_original: usa o nome do arquivo como nome da aba quando True.
        log_callback: função para registrar mensagens no UI.
        progress_callback: função para atualizar progresso (atual, total).
    """
    if not lista_arquivos:
        raise FileNotFoundError("Nenhum arquivo selecionado.")

    if log_callback:
        log_callback(f"Total de arquivos selecionados: {len(lista_arquivos)}")

    linhas_saida: list[pd.DataFrame] = []
    total_arquivos = len(lista_arquivos)

    for idx, caminho in enumerate(lista_arquivos, start=1):
        arquivo = Path(caminho)
        if log_callback:
            log_callback(f"Processando: {arquivo.name}")

        nome_uc = extrair_nome_uc(arquivo.name)
        df = pd.read_excel(arquivo, sheet_name=0)

        col_nome = "Nome"
        col_sobrenome = "Sobrenome"
        col_total_original = "Total do curso (Real)"

        for col in (col_nome, col_sobrenome, col_total_original):
            if col not in df.columns:
                raise ValueError(f"Coluna obrigatória '{col}' não encontrada em: {arquivo.name}")

        df["Aluno"] = df[col_nome].astype(str).str.strip() + " " + df[col_sobrenome].astype(str).str.strip()

        df_final = df[["Aluno", col_total_original]].copy()
        df_final = df_final.rename(columns={col_total_original: "Total do Curso"})
        df_final["UC / Relatório"] = nome_uc

        colunas_ordem = ["UC / Relatório", "Aluno", "Total do Curso"]
        df_final = df_final[colunas_ordem]

        if df_final.empty:
            if log_callback:
                log_callback(f"Nenhuma linha de dados em {arquivo.name}; arquivo ignorado.")
            if progress_callback:
                progress_callback(idx, total_arquivos)
            continue

        df_final.attrs["arquivo_origem"] = arquivo.name
        linhas_saida.append(df_final)

        if progress_callback:
            progress_callback(idx, total_arquivos)

    if not linhas_saida:
        raise ValueError("Nenhuma linha gerada.")

    with pd.ExcelWriter(arquivo_saida, engine="openpyxl") as writer:
        if dividir_por_uc:
            usados: dict[str, int] = {}
            for df_final in linhas_saida:
                nome_uc = df_final["UC / Relatório"].iloc[0]
                base_name = (
                    Path(df_final.attrs.get("arquivo_origem", nome_uc)).stem
                    if manter_nome_original
                    else nome_uc
                )

                contador = usados.get(base_name, 0)
                if contador == 0:
                    sheet_name = base_name[:31]
                else:
                    sufixo = f"_{contador}"
                    sheet_name = f"{base_name[:31 - len(sufixo)]}{sufixo}"
                usados[base_name] = contador + 1

                df_final.drop(columns=["UC / Relatório"]).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
                ws = writer.sheets[sheet_name]
                formatar_worksheet(ws)
        else:
            df_saida = pd.concat(linhas_saida, ignore_index=True)
            sheet_name = "Consolidado"
            df_saida.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            formatar_worksheet(ws)

    if log_callback:
        log_callback(f"Arquivo gerado: {arquivo_saida}")
