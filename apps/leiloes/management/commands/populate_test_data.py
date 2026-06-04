from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from apps.leiloes.models import ImovelCaixa
import random


class Command(BaseCommand):
    help = 'Popula banco de dados com imóveis de teste da Caixa'

    CIDADES = {
        'SP': ['São Paulo', 'Campinas', 'Santos', 'Ribeirão Preto', 'Sorocaba'],
        'RJ': ['Rio de Janeiro', 'Niterói', 'Duque de Caxias', 'Nova Iguaçu'],
        'MG': ['Belo Horizonte', 'Uberlândia', 'Juiz de Fora', 'Contagem'],
        'BA': ['Salvador', 'Feira de Santana', 'Vitória da Conquista'],
        'RS': ['Porto Alegre', 'Caxias do Sul', 'Pelotas'],
        'PR': ['Curitiba', 'Londrina', 'Maringá'],
    }

    TIPOS = ['apto', 'casa', 'sala', 'lote', 'galpao']
    RUAS = [
        'Rua das Flores', 'Avenida Paulista', 'Rua Brasil', 'Avenida Central',
        'Rua Marechal', 'Avenida Rio Branco', 'Rua das Acácias', 'Avenida Dez de Março'
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Número de imóveis para criar (padrão: 30)'
        )

    def handle(self, *args, **options):
        count = options['count']
        created = 0

        for i in range(count):
            # Seleciona estado e cidade aleatórios
            estado = random.choice(list(self.CIDADES.keys()))
            cidade = random.choice(self.CIDADES[estado])
            tipo = random.choice(self.TIPOS)

            # Gera dados aleatórios
            numero = random.randint(1, 5000)
            rua = random.choice(self.RUAS)
            endereco = f"{rua}, {numero}"
            if tipo == 'apto':
                endereco += f", Apto {random.randint(101, 9999)}"

            valor_avaliacao = Decimal(random.randint(100000, 1000000))
            desconto = Decimal(random.randint(5, 35))
            valor_minimo_lance = valor_avaliacao * (Decimal(100 - int(desconto)) / Decimal(100))

            data_leilao = timezone.now().date() + timedelta(days=random.randint(1, 60))
            hora_leilao = f"{random.randint(8, 17):02d}:{random.randint(0, 59):02d}:00"

            formas_pagamento = {
                'a_vista': random.choice([True, False]),
                'fgts': random.choice([True, False]),
                'financiamento': random.choice([True, False]),
                'consorcio': random.choice([True, False]),
                'parcelado': random.choice([True, False]),
            }

            try:
                imovel = ImovelCaixa.objects.create(
                    imovel_id_caixa=f"CAIXA_{estado}_{i}_{timezone.now().timestamp()}",
                    endereco=endereco,
                    cidade=cidade,
                    estado=estado,
                    cep=f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
                    tipo=tipo,
                    quartos=random.randint(1, 5) if tipo == 'apto' else None,
                    area_util=Decimal(random.randint(50, 300)) if tipo in ['apto', 'casa'] else None,
                    valor_avaliacao=valor_avaliacao,
                    percentual_desconto=desconto,
                    valor_minimo_lance=valor_minimo_lance,
                    valor_final=valor_minimo_lance,
                    data_leilao=data_leilao,
                    hora_leilao=hora_leilao,
                    tipo_leilao=random.choice(['extra', 'judicial']),
                    formas_pagamento=formas_pagamento,
                    edital_url=f"https://www.caixa.gov.br/edital/{i}",
                    matricula_url=f"https://www.caixa.gov.br/matricula/{i}",
                    ocupado=random.choice([True, False]),
                    pendencias=random.choice([[], ["IPTU em atraso"], ["Condomínio"], ["IPTU e Condomínio"]]),
                    possui_penhora=random.choice([True, False]),
                )
                created += 1
                self.stdout.write(f'✓ Criado: {imovel.endereco} - {cidade}/{estado}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Erro ao criar: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ {created} imóveis criados com sucesso!'))
