from django.core.management.base import BaseCommand

from apps.calculadora.services.cartorio_fontes import monitorar_fontes_cartorio


class Command(BaseCommand):
    help = "Monitora URLs oficiais de custos cartorários e cria eventos pendentes quando há mudança."

    def add_arguments(self, parser):
        parser.add_argument("--uf", help="Filtra uma UF específica.")
        parser.add_argument("--fonte-id", type=int, help="Monitora apenas uma fonte específica.")

    def handle(self, *args, **options):
        resultado = monitorar_fontes_cartorio(
            uf=options.get("uf"),
            fonte_id=options.get("fonte_id"),
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Concluído: "
                f"{resultado['fontes']} fontes, "
                f"{resultado['alteradas']} alteradas, "
                f"{resultado['sem_mudanca']} sem mudança, "
                f"{resultado['erros']} erros, "
                f"{resultado['eventos']} eventos novos."
            )
        )
