from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.calculadora.models import (
    CartorioFaixa,
    CartorioFonteMonitorada,
    CartorioRegraExtra,
    CartorioTabela,
)
from core.calculos import cartorio


TABELAS = {
    "BA": {"ano": 2026, "escritura": cartorio.TABELA_BA, "registro": cartorio.TABELA_BA},
    "SP": {"ano": 2026, "escritura": cartorio.TABELA_SP_ESCRITURA, "registro": cartorio.TABELA_SP_REGISTRO},
    "RJ": {"ano": 2026, "escritura": cartorio.TABELA_RJ, "registro": cartorio.TABELA_RJ},
    "MG": {"ano": 2026, "escritura": cartorio.TABELA_MG, "registro": cartorio.TABELA_MG},
    "PR": {"ano": 2026, "escritura": cartorio.TABELA_PR, "registro": cartorio.TABELA_PR},
    "RS": {"ano": 2026, "escritura": cartorio.TABELA_RS, "registro": cartorio.TABELA_RS},
    "PE": {"ano": 2025, "escritura": cartorio.TABELA_PE, "registro": cartorio.TABELA_PE},
    "CE": {"ano": 2025, "escritura": cartorio.TABELA_CE, "registro": cartorio.TABELA_CE},
    "DF": {"ano": 2025, "escritura": cartorio.TABELA_DF, "registro": cartorio.TABELA_DF},
    "SC": {"ano": 2025, "escritura": cartorio.TABELA_SC, "registro": cartorio.TABELA_SC},
    "GO": {"ano": 2025, "escritura": cartorio.TABELA_GO, "registro": cartorio.TABELA_GO},
    "ES": {"ano": 2025, "escritura": cartorio.TABELA_ES, "registro": cartorio.TABELA_ES},
}

EXTRAS = {
    "RJ": {"ano": 2026, "nome": "FUNDPERJ", "percentual": Decimal("0.1000")},
    "PR": {"ano": 2026, "nome": "FUNREJUS", "percentual": Decimal("0.2000")},
}

FONTES_URL = {
    "BA": "https://www.tjba.jus.br/extrajudicial/tabelas-de-custas/",
    "SP": "https://extrajudicial.tjsp.jus.br/pexPtl/listaLinksPortal.do",
    "RJ": "https://www3.tjrj.jus.br/portalextrajudicial/emolumentos.aspx",
}


class Command(BaseCommand):
    help = "Carrega as tabelas cartorárias legadas no banco com metadados de fonte e vigência."

    def add_arguments(self, parser):
        parser.add_argument(
            "--uf",
            action="append",
            help="UF a carregar. Pode repetir. Se omitido, carrega todas as UFs disponíveis.",
        )
        parser.add_argument(
            "--status",
            choices=[choice[0] for choice in CartorioTabela.STATUS_CHOICES],
            default=CartorioTabela.STATUS_PENDENTE,
            help="Status inicial das tabelas criadas/atualizadas.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Substitui as faixas das tabelas existentes pelo conteúdo do seed.",
        )

    def handle(self, *args, **options):
        ufs = {uf.upper() for uf in options["uf"]} if options["uf"] else set(TABELAS)
        status = options["status"]
        replace = options["replace"]

        criadas = atualizadas = faixas_criadas = extras_salvos = fontes_salvas = 0
        for uf in sorted(ufs):
            dados = TABELAS.get(uf)
            if not dados:
                self.stderr.write(self.style.WARNING(f"UF sem seed disponível: {uf}"))
                continue

            ano = dados["ano"]
            fonte_nome = f"Tabela legada do sistema - TJ-{uf}"
            fonte_url = FONTES_URL.get(uf, "")
            observacoes = (
                "Importada do arquivo core/calculos/cartorio.py para permitir "
                "versionamento, auditoria e validação anual. Conferir valores "
                "contra a tabela oficial antes de marcar como validada."
            )
            if fonte_url:
                CartorioFonteMonitorada.objects.update_or_create(
                    url=fonte_url,
                    defaults={
                        "uf": uf,
                        "nome": f"Fonte oficial TJ-{uf}",
                        "ativa": True,
                        "observacoes": (
                            "Criada pelo seed de custos cartorários. O monitoramento "
                            "detecta mudanças na fonte, mas a validação das faixas é manual."
                        ),
                    },
                )
                fontes_salvas += 1

            for tipo in ("escritura", "registro"):
                tabela, created = CartorioTabela.objects.update_or_create(
                    uf=uf,
                    ano=ano,
                    tipo=tipo,
                    vigente_inicio=date(ano, 1, 1),
                    defaults={
                        "fonte_nome": fonte_nome,
                        "fonte_url": fonte_url,
                        "observacoes": observacoes,
                        "status": status,
                        "ativo": True,
                    },
                )
                criadas += int(created)
                atualizadas += int(not created)

                if replace or created or not tabela.faixas.exists():
                    tabela.faixas.all().delete()
                    objetos = [
                        CartorioFaixa(
                            tabela=tabela,
                            ordem=ordem,
                            limite_superior=None if limite == float("inf") else Decimal(str(limite)),
                            valor=Decimal(str(valor)),
                        )
                        for ordem, (limite, valor) in enumerate(dados[tipo], start=1)
                    ]
                    CartorioFaixa.objects.bulk_create(objetos)
                    faixas_criadas += len(objetos)

            extra = EXTRAS.get(uf)
            if extra:
                CartorioRegraExtra.objects.update_or_create(
                    uf=uf,
                    ano=extra["ano"],
                    nome=extra["nome"],
                    vigente_inicio=date(extra["ano"], 1, 1),
                    defaults={
                        "percentual": extra["percentual"],
                        "fonte_nome": fonte_nome,
                        "fonte_url": fonte_url,
                        "observacoes": observacoes,
                        "status": status,
                        "ativo": True,
                    },
                )
                extras_salvos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {criadas} tabelas criadas, {atualizadas} atualizadas, "
                f"{faixas_criadas} faixas salvas, {extras_salvos} extras salvos, "
                f"{fontes_salvas} fontes monitoradas."
            )
        )
