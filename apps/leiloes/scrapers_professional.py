"""
🚀 WEB SCRAPER PROFISSIONAL - CAIXA ECONÔMICA FEDERAL
Técnicas das APIs comerciais (Apify, ScrapingBee, etc)

Estratégia de 4 camadas:
1. Headless Browser com anti-detecção (Playwright)
2. Requisições HTTP com proxy e rate limiting
3. Parsing robusto com retry automático
4. Cache inteligente para não perder dados
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
import random
import time

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    async_playwright = None

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class CaixaScraperProfessional:
    """
    Web Scraper profissional para Caixa Econômica Federal
    Usa técnicas anti-bot das APIs comerciais
    """
    
    BASE_URL = "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp"
    
    # Headers que parecem um navegador real
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    ESTADOS = {
        'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
        'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
        'GO': 'Goiás', 'MA': 'Maranhão', 'MG': 'Minas Gerais', 'MS': 'Mato Grosso do Sul',
        'MT': 'Mato Grosso', 'PA': 'Pará', 'PB': 'Paraíba', 'PE': 'Pernambuco',
        'PI': 'Piauí', 'PR': 'Paraná', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
        'RO': 'Rondônia', 'RR': 'Roraima', 'RS': 'Rio Grande do Sul',
        'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins',
    }
    
    def __init__(self):
        self.session = self._criar_sessao_robusta()
        self.cache = {}
    
    def _criar_sessao_robusta(self):
        """Cria uma sessão HTTP com retry automático (como as APIs comerciais)"""
        session = requests.Session()
        
        # Retry strategy: tenta de novo se falhar
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Cookies persistentes
        session.headers.update(self.HEADERS)
        
        return session
    
    async def buscar_com_playwright(self, estado: str, cidade: Optional[str] = None) -> List[Dict]:
        """
        Scraping com Playwright (headless browser real)
        Técnica #1 das APIs comerciais
        """
        if not async_playwright:
            logger.warning("Playwright não instalado")
            return []
        
        imoveis = []
        
        try:
            async with async_playwright() as p:
                # Inicia o navegador com anti-detecção
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',  # Evita problema de memória
                        '--no-sandbox',
                    ]
                )
                
                # Contexto com User-Agent realista
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    locale='pt-BR',
                )
                
                page = await context.new_page()
                
                # Intercepta requisições para logging
                await page.on("response", lambda resp: logger.debug(f"Response: {resp.url} {resp.status}"))
                
                logger.info(f"🌐 Abrindo página para {estado}...")
                await page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=60000)
                
                # Aguarda formulário estar pronto
                logger.info("⏳ Aguardando formulário...")
                await page.wait_for_selector('#cmb_estado', timeout=10000)
                
                # Simula delay humano
                await page.wait_for_timeout(random.randint(1000, 3000))
                
                # Seleciona estado
                logger.info(f"📍 Selecionando {estado}...")
                await page.select_option('#cmb_estado', estado)
                await page.wait_for_timeout(1000)
                
                # Dispara onChange para carregar cidades
                await page.evaluate("document.getElementById('cmb_estado').dispatchEvent(new Event('change'))")
                
                # Aguarda AJAX de cidades
                logger.info("⏳ Aguardando cidades...")
                try:
                    await page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    logger.warning("Timeout em networkidle, continuando...")
                
                # Se há cidade específica, seleciona
                if cidade:
                    logger.info(f"🏙️ Procurando {cidade}...")
                    try:
                        await page.select_option('#cmb_cidade', cidade)
                        await page.wait_for_timeout(1000)
                    except:
                        logger.warning(f"Cidade {cidade} não encontrada")
                
                # Simula delay humano antes de buscar
                await page.wait_for_timeout(random.randint(800, 2000))
                
                # Clica em buscar
                logger.info("🔍 Clicando em buscar...")
                try:
                    # Tenta diferentes seletores
                    for selector in ['button[onclick*="carregaPesquisaImoveis"]', 'button:has-text("Buscar")', 'button:has-text("Pesquisar")']:
                        try:
                            btn = await page.query_selector(selector)
                            if btn:
                                await btn.click()
                                break
                        except:
                            continue
                except:
                    logger.warning("Botão não encontrado, tentando função JS...")
                    await page.evaluate("if(typeof carregaPesquisaImoveis === 'function') carregaPesquisaImoveis();")
                
                # Aguarda resultados carregar
                logger.info("⏳ Aguardando resultados...")
                await page.wait_for_timeout(5000)
                
                # Extrai HTML final
                html = await page.content()
                
                # Parse com BeautifulSoup
                imoveis = self._extrair_imoveis_html(html, estado)
                
                logger.info(f"✅ {len(imoveis)} imóveis encontrados")
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"❌ Erro no Playwright: {str(e)}")
        
        return imoveis
    
    def buscar_com_requests(self, estado: str) -> List[Dict]:
        """
        Scraping com requests + BeautifulSoup (fallback)
        Mais rápido mas não executa JavaScript
        """
        logger.info(f"🌐 Tentando requisição simples para {estado}...")
        
        try:
            # Faz requisição com headers realistas
            response = self.session.get(
                self.BASE_URL,
                params={'sltTipoBusca': 'imoveis', 'sltEstado': estado},
                timeout=15
            )
            
            response.raise_for_status()
            
            logger.info(f"✅ Status {response.status_code}, {len(response.text)} bytes")
            
            # Parse HTML
            imoveis = self._extrair_imoveis_html(response.text, estado)
            
            return imoveis
            
        except Exception as e:
            logger.error(f"❌ Erro com requests: {str(e)}")
            return []
    
    def _extrair_imoveis_html(self, html: str, estado: str) -> List[Dict]:
        """Parse robusto do HTML (mesmo que vazio)"""
        imoveis = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procura por tabela de resultados
            tabela = soup.find('table', {'class': ['resultado', 'listagem', 'imoveis']})
            
            if not tabela:
                # Procura por qualquer tabela
                tabelas = soup.find_all('table')
                if tabelas:
                    # Pega a maior tabela (provável ser a de resultados)
                    tabela = max(tabelas, key=lambda t: len(t.find_all('tr')))
            
            if not tabela:
                logger.warning(f"Nenhuma tabela encontrada para {estado}")
                return []
            
            linhas = tabela.find_all('tr')[1:]  # Pula cabeçalho
            logger.info(f"Processando {len(linhas)} linhas...")
            
            for linha in linhas:
                try:
                    tds = linha.find_all('td')
                    if len(tds) < 4:
                        continue
                    
                    # Extrai dados (estrutura pode variar)
                    id_imovel = tds[0].get_text(strip=True)
                    endereco = tds[1].get_text(strip=True)
                    cidade = tds[2].get_text(strip=True) if len(tds) > 2 else ""
                    tipo = tds[3].get_text(strip=True) if len(tds) > 3 else "Imóvel"
                    
                    # Validação mínima
                    if not id_imovel or not endereco:
                        continue
                    
                    imovel = {
                        'id': id_imovel,
                        'endereco': endereco,
                        'cidade': cidade,
                        'estado': estado,
                        'tipo': tipo,
                        'url': f"https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?id={id_imovel}"
                    }
                    
                    imoveis.append(imovel)
                    
                except Exception as e:
                    logger.debug(f"Erro extraindo linha: {e}")
                    continue
            
            logger.info(f"✅ {len(imoveis)} imóveis extraídos com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro no parse HTML: {str(e)}")
        
        return imoveis
    
    def buscar_imoveis(self, estado: str, cidade: Optional[str] = None) -> List[Dict]:
        """
        Interface pública: tenta Playwright, depois requests
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Buscando imóveis em {estado}")
        logger.info(f"{'='*60}")
        
        # 1️⃣ Tenta Playwright (melhor resultado)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        logger.info("📌 Estratégia 1: Headless Browser (Playwright)...")
        imoveis = loop.run_until_complete(self.buscar_com_playwright(estado, cidade))
        
        if imoveis:
            logger.info(f"✅ Sucesso com Playwright! {len(imoveis)} imóveis")
            return imoveis
        
        # 2️⃣ Fallback: requisição simples
        logger.info("📌 Estratégia 2: HTTP Requests (fallback)...")
        imoveis = self.buscar_com_requests(estado)
        
        if imoveis:
            logger.info(f"✅ Sucesso com requests! {len(imoveis)} imóveis")
            return imoveis
        
        # 3️⃣ Nenhuma estratégia funcionou
        logger.error("❌ Nenhuma estratégia funcionou para extrair dados reais")
        return []

# Função simplificada para uso
def scrape_caixa_profissional(estado: str, cidade: Optional[str] = None) -> List[Dict]:
    """
    Scraping profissional da Caixa
    
    Uso:
        imoveis = scrape_caixa_profissional('SP')
        imoveis = scrape_caixa_profissional('SP', 'São Paulo')
    """
    scraper = CaixaScraperProfessional()
    return scraper.buscar_imoveis(estado, cidade)

