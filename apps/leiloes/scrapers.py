"""
Scraper para leilões de imóveis da Caixa Econômica Federal
Sem dependências externas pagas (apenas requests + BeautifulSoup)

URL: https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis
"""

import requests
from bs4 import BeautifulSoup
import logging
from decimal import Decimal
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)


class CaixaLeiloesScraper:
    """Scraper para leilões da Caixa Econômica"""

    # URLs da Caixa Econômica (venda-imoveis.caixa.gov.br)
    BASE_URL = "https://venda-imoveis.caixa.gov.br"
    BUSCA_URL = f"{BASE_URL}/sistema/busca-imovel.asp"
    CARREGAR_CIDADES_URL = f"{BASE_URL}/sistema/carregaListaCidades.asp"
    CARREGAR_BAIRROS_URL = f"{BASE_URL}/sistema/carregaListaBairros.asp"
    BUSCAR_IMOVEIS_URL = f"{BASE_URL}/sistema/carregaPesquisaImoveis.asp"

    # Headers para simular navegador real
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': BUSCA_URL,
    }

    # Estados e siglas
    ESTADOS = {
        'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
        'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
        'GO': 'Goiás', 'MA': 'Maranhão', 'MG': 'Minas Gerais', 'MS': 'Mato Grosso do Sul',
        'MT': 'Mato Grosso', 'PA': 'Pará', 'PB': 'Paraíba', 'PE': 'Pernambuco',
        'PI': 'Piauí', 'PR': 'Paraná', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
        'RO': 'Rondônia', 'RR': 'Roraima', 'RS': 'Rio Grande do Sul',
        'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins',
    }

    @staticmethod
    def buscar_imoveis(estado, cidade=None, modalidade=14):
        """
        Busca imóveis em leilão na Caixa

        Args:
            estado: Sigla do estado (SP, RJ, BA, etc)
            cidade: Nome da cidade (opcional)
            modalidade: 14=Leilão SFI, 30=Exercício Direito, 21=Licitação, 33=Venda Online, 34=Venda Direta Online

        Returns:
            Lista de imóveis encontrados
        """
        try:
            logger.info(f"Buscando imóveis em {estado}/{cidade or 'todas cidades'}...")

            # Parâmetros POST para a busca
            payload = {
                'cmb_estado': estado.upper(),
                'cmb_modalidade': str(modalidade),
                'cmb_cidade': cidade or '',
                'cmb_bairro': '',
                'cmb_financiamento': '',
                'cmb_tipo': '',
                'cmb_quartos': '',
                'cmb_vagas': '',
                'cmb_area': '',
                'cmb_preco': '',
                'hdnPagNum': 1,
            }

            response = requests.post(
                CaixaLeiloesScraper.BUSCAR_IMOVEIS_URL,
                data=payload,
                headers=CaixaLeiloesScraper.HEADERS,
                timeout=30
            )
            response.raise_for_status()

            # Trata resposta HTML com BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            imoveis = CaixaLeiloesScraper._extrair_imoveis_html(soup)

            logger.info(f"✓ {len(imoveis)} imóveis encontrados em {estado}")
            return imoveis

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar imóveis em {estado}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {str(e)}")
            return []

    @staticmethod
    def _extrair_imoveis_html(soup):
        """
        Extrai dados de imóveis a partir do HTML retornado
        """
        imoveis = []

        # Procura por linhas da tabela de resultados
        linhas = soup.find_all('tr', class_='linha-resultado')

        if not linhas:
            # Tenta estrutura alternativa (divs com classe imovel)
            linhas = soup.find_all('div', class_=['imovel-card', 'imovel-item'])

        for linha in linhas:
            try:
                imovel = CaixaLeiloesScraper._extrair_imovel_linha(linha)
                if imovel:
                    imoveis.append(imovel)
            except Exception as e:
                logger.warning(f"Erro ao extrair imóvel de linha: {str(e)}")
                continue

        return imoveis

    @staticmethod
    def _extrair_imovel_linha(linha):
        """
        Extrai dados de uma linha/card de imóvel
        """
        try:
            # Tenta extrair campos de <tr>
            tds = linha.find_all('td')

            if len(tds) >= 3:
                imovel_data = {
                    'id': tds[0].text.strip() if tds[0] else '',
                    'endereco': tds[1].text.strip() if len(tds) > 1 else '',
                    'cidade': tds[2].text.strip() if len(tds) > 2 else '',
                    'tipo': tds[3].text.strip() if len(tds) > 3 else '',
                    'valor': tds[4].text.strip() if len(tds) > 4 else '0',
                }

                # Valida se tem pelo menos id e endereço
                if imovel_data['id'] and imovel_data['endereco']:
                    return imovel_data

            # Tenta extrair de <div>
            spans = linha.find_all('span')
            if len(spans) >= 3:
                imovel_data = {
                    'id': spans[0].text.strip() if spans[0] else '',
                    'endereco': spans[1].text.strip() if len(spans) > 1 else '',
                    'cidade': spans[2].text.strip() if len(spans) > 2 else '',
                }

                if imovel_data['id'] and imovel_data['endereco']:
                    return imovel_data

        except Exception as e:
            logger.warning(f"Erro ao extrair dados: {str(e)}")

        return None

    @staticmethod
    def normalizar_imovel(imovel_data):
        """
        Normaliza dados do imóvel para formato padrão
        """
        try:
            # Extrai valor numérico
            valor_str = imovel_data.get('valor', '0').replace('R$', '').replace('.', '').replace(',', '.')
            valor = Decimal(valor_str) if valor_str else Decimal(0)

            return {
                'imovelId': imovel_data.get('id', ''),
                'endereco': imovel_data.get('endereco', ''),
                'cidade': imovel_data.get('cidade', ''),
                'estado': imovel_data.get('estado', ''),
                'cep': imovel_data.get('cep', ''),
                'tipo': imovel_data.get('tipo', 'imovel').lower(),
                'quartos': imovel_data.get('quartos'),
                'area_util': imovel_data.get('area'),
                'avaliacao': valor,
                'desconto': Decimal(str(imovel_data.get('desconto', 0))),
                'valorMinimoLance': valor * (Decimal(100 - Decimal(imovel_data.get('desconto', 0))) / Decimal(100)),
                'dataLeilao': imovel_data.get('data_leilao', ''),
                'horaLeilao': imovel_data.get('hora_leilao', ''),
                'tipoLeilao': 'publica',
                'foto_url': imovel_data.get('foto'),
                'edital_url': imovel_data.get('edital_url'),
                'matricula': imovel_data.get('matricula', ''),
                'aceita_a_vista': bool(imovel_data.get('a_vista')),
                'aceita_fgts': bool(imovel_data.get('fgts')),
                'aceita_financiamento': bool(imovel_data.get('financiamento')),
                'aceita_consorcio': bool(imovel_data.get('consorcio')),
            }
        except Exception as e:
            logger.error(f"Erro ao normalizar imóvel: {str(e)}")
            return None


def buscar_leiloes_caixa(estado, cidade=None):
    """
    Função simplificada para buscar leilões da Caixa

    Usage:
        imoveis = buscar_leiloes_caixa('SP')
        imoveis = buscar_leiloes_caixa('SP', 'São Paulo')
    """
    scraper = CaixaLeiloesScraper()
    imoveis_raw = scraper.buscar_imoveis(estado, cidade)

    # Normaliza cada imóvel
    imoveis = []
    for imovel_raw in imoveis_raw:
        imovel_normalizado = scraper.normalizar_imovel(imovel_raw)
        if imovel_normalizado:
            imoveis.append(imovel_normalizado)

    return imoveis
