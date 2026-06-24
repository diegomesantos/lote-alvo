from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.leiloes.caixa_csv import (
    ESTADOS,
    baixar_csv_caixa,
    enriquecer_imoveis_caixa,
    filtrar_detalhe_pendente,
    importar_csv_caixa,
    marcar_imoveis_ausentes_como_inativos,
    ordenar_detalhe_pendente,
)
from apps.leiloes.models import ImovelCaixa


class Command(BaseCommand):
    help = "Sincroniza imóveis da Caixa via CSV oficial e, opcionalmente, enriquece detalhes por imóvel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--estado",
            default="geral",
            help="UF para baixar/importar, ou 'geral' para todos em um CSV. Padrão: geral",
        )
        parser.add_argument(
            "--todos-estados",
            action="store_true",
            help="Baixa um CSV por UF em vez do CSV geral",
        )
        parser.add_argument(
            "--arquivo",
            help="Importa um CSV já baixado, sem acessar a Caixa para download",
        )
        parser.add_argument(
            "--destino-dir",
            default="media/caixa_csv",
            help="Diretório para salvar os CSVs baixados",
        )
        parser.add_argument(
            "--limite",
            type=int,
            help="Limita a quantidade de linhas importadas do CSV, útil para testes",
        )
        parser.add_argument(
            "--enriquecer",
            action="store_true",
            help="Após importar, acessa a página de cada imóvel para foto, edital, matrícula e detalhes",
        )
        parser.add_argument(
            "--inativar-ausentes",
            action="store_true",
            help="Marca como inativos os imóveis que não vierem no CSV importado",
        )
        parser.add_argument(
            "--max-detalhes",
            type=int,
            help="Quantidade máxima de imóveis a enriquecer nesta execução",
        )
        parser.add_argument(
            "--somente-pendentes-detalhe",
            action="store_true",
            help="Enriquece apenas imóveis sem detalhe_atualizado_em",
        )
        parser.add_argument(
            "--intervalo",
            type=float,
            default=1.0,
            help="Pausa em segundos entre páginas de detalhe. Padrão: 1.0",
        )
        parser.add_argument(
            "--headful",
            action="store_true",
            help="Abre Chromium visível para depuração",
        )

    def handle(self, *args, **options):
        if options["limite"] and options["inativar_ausentes"]:
            raise CommandError("--inativar-ausentes não deve ser usado junto com --limite")

        sincronizacao_inicio = timezone.now()
        arquivos = []
        ids_importados = []

        if options["arquivo"]:
            arquivo = Path(options["arquivo"])
            if not arquivo.exists():
                raise CommandError(f"Arquivo não encontrado: {arquivo}")
            arquivos.append(arquivo)
        elif options["todos_estados"]:
            for estado in ESTADOS:
                self.stdout.write(f"Baixando CSV da Caixa para {estado}...")
                arquivos.append(
                    baixar_csv_caixa(
                        estado=estado,
                        destino_dir=options["destino_dir"],
                        headless=not options["headful"],
                    )
                )
        else:
            estado = options["estado"]
            self.stdout.write(f"Baixando CSV da Caixa para {estado}...")
            arquivos.append(
                baixar_csv_caixa(
                    estado=estado,
                    destino_dir=options["destino_dir"],
                    headless=not options["headful"],
                )
            )

        total_criados = 0
        total_atualizados = 0
        total_reativados = 0

        for arquivo in arquivos:
            self.stdout.write(f"Importando {arquivo}...")
            resultado = importar_csv_caixa(arquivo, limite=options["limite"])
            ids_importados.extend(resultado["ids"])
            total_criados += resultado["criados"]
            total_atualizados += resultado["atualizados"]
            total_reativados += resultado.get("reativados", 0)

            metadata = resultado["metadata"]
            data_geracao = metadata.get("data_geracao")
            data_msg = data_geracao.strftime("%d/%m/%Y") if data_geracao else "desconhecida"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{arquivo.name}: {resultado['criados']} criados, "
                    f"{resultado['atualizados']} atualizados, "
                    f"{resultado.get('reativados', 0)} reativados, geração {data_msg}"
                )
            )

        inativados = 0
        if options["inativar_ausentes"]:
            estado_inativacao = None
            if not options["todos_estados"] and options["estado"].lower() != "geral":
                estado_inativacao = options["estado"].upper()

            inativados = marcar_imoveis_ausentes_como_inativos(
                ids_importados,
                estado=estado_inativacao,
                sincronizacao_inicio=sincronizacao_inicio,
            )
            escopo = estado_inativacao or "todos os estados"
            self.stdout.write(
                self.style.WARNING(
                    f"{inativados} imóvel(is) ausente(s) no CSV marcados como inativos em {escopo}"
                )
            )

        detalhe_msg = ""
        if options["enriquecer"]:
            queryset = ImovelCaixa.objects.filter(
                ativo_caixa=True,
                ultima_sincronizacao_caixa__gte=sincronizacao_inicio,
            )
            if options["somente_pendentes_detalhe"]:
                queryset = filtrar_detalhe_pendente(queryset)
                queryset = ordenar_detalhe_pendente(queryset)
            else:
                queryset = queryset.order_by("estado", "cidade", "imovel_id_caixa")
            if options["max_detalhes"]:
                queryset = queryset[: options["max_detalhes"]]

            imoveis = list(queryset)
            self.stdout.write(f"Enriquecendo {len(imoveis)} imóvel(is) na Caixa...")
            detalhe = enriquecer_imoveis_caixa(
                imoveis,
                intervalo=options["intervalo"],
                headless=not options["headful"],
            )
            detalhe_msg = (
                f"\nDetalhes: {detalhe['atualizados']} atualizados, "
                f"{detalhe['inativados']} inativados, "
                f"{len(detalhe['erros'])} erro(s)"
            )
            if detalhe["erros"]:
                for erro in detalhe["erros"][:10]:
                    self.stdout.write(self.style.WARNING(f"  - {erro}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Sincronização concluída: {total_criados} criados, "
                f"{total_atualizados} atualizados, {total_reativados} reativados, "
                f"{inativados} inativados{detalhe_msg}"
            )
        )
