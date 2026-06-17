from django.core.management.base import BaseCommand

from apps.leiloes.caixa_csv import extrair_regras_despesas
from apps.leiloes.models import ImovelCaixa


class Command(BaseCommand):
    help = (
        "Reprocessa regras_pagamento_texto já salvas no enriquecimento e preenche "
        "os campos estruturados despesa_condominio / despesa_tributos. "
        "Não acessa a Caixa: trabalha apenas sobre dados já presentes no banco."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas mostra o que mudaria, sem salvar",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        queryset = ImovelCaixa.objects.filter(detalhe_atualizado_em__isnull=False)

        analisados = 0
        atualizados = 0
        for imovel in queryset.iterator():
            detalhe_caixa = (imovel.detalhes or {}).get("detalhe_caixa") or {}
            regras_texto = detalhe_caixa.get("regras_pagamento_texto") or ""
            if not regras_texto.strip():
                continue

            analisados += 1
            regras = extrair_regras_despesas(regras_texto)
            mudou = (
                imovel.despesa_condominio != regras["despesa_condominio"]
                or imovel.despesa_tributos != regras["despesa_tributos"]
            )
            if not mudou:
                continue

            atualizados += 1
            if dry_run:
                self.stdout.write(
                    f"{imovel.imovel_id_caixa}: condomínio "
                    f"{imovel.despesa_condominio} -> {regras['despesa_condominio']}, "
                    f"tributos {imovel.despesa_tributos} -> {regras['despesa_tributos']}"
                )
                continue

            imovel.despesa_condominio = regras["despesa_condominio"]
            imovel.despesa_tributos = regras["despesa_tributos"]
            imovel.save(update_fields=["despesa_condominio", "despesa_tributos", "atualizado_em"])

        sufixo = " (dry-run, nada salvo)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"Concluído{sufixo}: {analisados} com regras, {atualizados} atualizados."
        ))
