from django.core.management.base import BaseCommand
from apps.leiloes.views import sincronizar_imoveis_caixa


class Command(BaseCommand):
    help = 'Sincroniza imóveis da Caixa Econômica Federal via Apify'

    def add_arguments(self, parser):
        parser.add_argument(
            '--estado',
            type=str,
            default='SP',
            help='Estado para sincronizar (padrão: SP)'
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Sincroniza todos os estados principais'
        )
        parser.add_argument(
            '--teste',
            action='store_true',
            help='Usa dados simulados para teste (padrão)'
        )
        parser.add_argument(
            '--apify',
            action='store_true',
            help='Tenta usar API Apify em vez de dados teste'
        )

    def handle(self, *args, **options):
        estados = [
            'SP', 'RJ', 'MG', 'BA', 'RS', 'PR', 'PE', 'CE', 'PA', 'SC'
        ] if options['todos'] else [options['estado']]

        # Define modo: teste por padrão, Apify apenas se --apify foi passado
        modo_teste = not options.get('apify', False)

        total_criados = 0
        total_atualizados = 0
        todos_erros = []

        modo_str = "TESTE" if modo_teste else "APIFY"
        self.stdout.write(self.style.WARNING(f'\n🔄 Sincronizando em modo {modo_str}'))

        for estado in estados:
            self.stdout.write(f'\n🔄 Sincronizando {estado}...')

            criados, atualizados, erros = sincronizar_imoveis_caixa(estado, modo_teste=modo_teste)

            total_criados += criados
            total_atualizados += atualizados
            todos_erros.extend(erros)

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {estado}: {criados} criados, {atualizados} atualizados'
                )
            )

            if erros:
                for erro in erros[:3]:  # Mostra primeiros 3 erros
                    self.stdout.write(self.style.WARNING(f'  ⚠️ {erro}'))

        # Resumo final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(
            f'✅ RESUMO FINAL\n'
            f'   Criados: {total_criados}\n'
            f'   Atualizados: {total_atualizados}\n'
            f'   Erros: {len(todos_erros)}'
        ))

        if todos_erros:
            self.stdout.write(self.style.WARNING(f'\n⚠️ Erros encontrados:'))
            for erro in todos_erros[:5]:
                self.stdout.write(f'  - {erro}')
