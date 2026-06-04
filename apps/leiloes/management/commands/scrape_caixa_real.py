"""
Django Management Command para scraper profissional da Caixa
Sintaxe:
    python manage.py scrape_caixa_real --estado SP
    python manage.py scrape_caixa_real --todos
    python manage.py scrape_caixa_real --estado BA --cidade Salvador
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from apps.leiloes.models import ImovelCaixa
from apps.leiloes.scrapers_simple import scrape_caixa_simples

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrape real de imóveis da Caixa Econômica Federal'
    
    ESTADOS = {
        'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
        'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
        'GO': 'Goiás', 'MA': 'Maranhão', 'MG': 'Minas Gerais', 'MS': 'Mato Grosso do Sul',
        'MT': 'Mato Grosso', 'PA': 'Pará', 'PB': 'Paraíba', 'PE': 'Pernambuco',
        'PI': 'Piauí', 'PR': 'Paraná', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
        'RO': 'Rondônia', 'RR': 'Roraima', 'RS': 'Rio Grande do Sul',
        'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins',
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--estado',
            type=str,
            help='Estado a scraper (ex: SP, RJ, BA)'
        )
        parser.add_argument(
            '--cidade',
            type=str,
            help='Cidade específica (opcional)'
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Scraper todos os estados'
        )
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Limpar dados antigos antes de scraper'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("""
╔════════════════════════════════════════════════════╗
║  🚀 WEB SCRAPER PROFISSIONAL - CAIXA ECONÔMICA    ║
╚════════════════════════════════════════════════════╝
        """))
        
        # Determina quais estados scraper
        if options['todos']:
            estados = list(self.ESTADOS.keys())
            self.stdout.write(f"🔄 Scraper {len(estados)} estados...")
        elif options['estado']:
            estados = [options['estado'].upper()]
        else:
            raise CommandError("Especifique --estado ou --todos")
        
        # Limpa dados antigos se solicitado
        if options['limpar']:
            self.stdout.write("🗑️  Limpando dados antigos...")
            ImovelCaixa.objects.all().delete()
        
        # Scraper cada estado
        total_imoveis = 0
        
        for estado in estados:
            if estado not in self.ESTADOS:
                self.stdout.write(self.style.ERROR(f"❌ Estado {estado} inválido"))
                continue
            
            self.stdout.write(f"\n📍 Scraper {estado} ({self.ESTADOS[estado]})...")
            
            try:
                # Usa scraper simples síncrono
                imoveis_raw = scrape_caixa_simples(estado, options.get('cidade'))
                
                if not imoveis_raw:
                    self.stdout.write(self.style.WARNING(f"⚠️  Nenhum imóvel encontrado para {estado}"))
                    continue
                
                # Salva no banco
                criados = 0
                atualizados = 0
                
                for imovel_data in imoveis_raw:
                    try:
                        imovel, created = ImovelCaixa.objects.get_or_create(
                            imovel_id_caixa=imovel_data['id'],
                            defaults={
                                'endereco': imovel_data['endereco'],
                                'cidade': imovel_data['cidade'],
                                'estado': imovel_data['estado'],
                                'tipo': 'outro',  # Will be updated later
                                'valor_avaliacao': 0,  # Will be updated with detail scrape
                                'percentual_desconto': 0,
                                'valor_minimo_lance': 0,
                            }
                        )
                        if created:
                            criados += 1
                        else:
                            atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao salvar {imovel_data['id']}: {e}")
                
                self.stdout.write(self.style.SUCCESS(
                    f"✅ {estado}: {criados} criados, {atualizados} atualizados"
                ))
                
                total_imoveis += len(imoveis_raw)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Erro ao scraper {estado}: {e}"))
                logger.exception(f"Erro em {estado}")
        
        self.stdout.write(self.style.SUCCESS(f"""
╔════════════════════════════════════════════════════╗
║ ✅ SCRAPING COMPLETO!                             ║
║ Total de imóveis: {total_imoveis}
╚════════════════════════════════════════════════════╝
        """))

