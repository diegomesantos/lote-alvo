"""
Scraper simplificado que funciona sem async
Usa Playwright de forma síncrona com workaround para o event loop
"""

import logging
from typing import List, Dict, Optional
import time
import random

logger = logging.getLogger(__name__)

def scrape_caixa_simples(estado: str, cidade: Optional[str] = None) -> List[Dict]:
    """
    Scraping sincronizado com Playwright
    Contorna problemas de async/event loop
    """
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright não instalado. Execute: pip install playwright")
        return []
    
    imoveis = []
    
    try:
        logger.info(f"🌐 Abrindo navegador para {estado}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            page = browser.new_page()
            
            # Acessa a página
            logger.info("📄 Carregando página...")
            page.goto(
                "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis",
                wait_until="domcontentloaded",
                timeout=60000
            )
            
            # Aguarda formulário
            logger.info("⏳ Aguardando formulário...")
            page.wait_for_selector("#cmb_estado", timeout=10000)
            
            # Seleciona estado
            logger.info(f"📍 Selecionando {estado}...")
            page.select_option("#cmb_estado", estado)
            time.sleep(random.uniform(1, 2))
            
            # Dispara evento de mudança
            page.evaluate("document.getElementById('cmb_estado').dispatchEvent(new Event('change'))")
            time.sleep(2)
            
            # Se tem cidade, seleciona
            if cidade:
                logger.info(f"🏙️ Tentando selecionar {cidade}...")
                try:
                    page.select_option("#cmb_cidade", cidade)
                    time.sleep(1)
                except:
                    logger.warning(f"Cidade {cidade} não disponível")
            
            # Aguarda um pouco
            time.sleep(random.uniform(1, 3))
            
            # Tenta clicar em buscar
            logger.info("🔍 Buscando imóveis...")
            try:
                page.click("button:has-text('Buscar')")
            except:
                try:
                    page.click("button:has-text('Pesquisar')")
                except:
                    logger.warning("Botão de busca não encontrado")
            
            # Aguarda resultados
            logger.info("⏳ Aguardando resultados...")
            time.sleep(4)
            
            # Extrai HTML
            html = page.content()
            
            # Parse com BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procura tabelas
            tabelas = soup.find_all('table')
            logger.info(f"   Encontradas {len(tabelas)} tabelas")
            
            if tabelas:
                # Tenta a maior tabela (provavelmente a de resultados)
                tabela = max(tabelas, key=lambda t: len(t.find_all('tr')))
                linhas = tabela.find_all('tr')[1:]  # Pula cabeçalho
                
                logger.info(f"   Processando {len(linhas)} linhas...")
                
                for linha in linhas:
                    try:
                        tds = linha.find_all('td')
                        if len(tds) < 2:
                            continue
                        
                        id_imovel = tds[0].get_text(strip=True)
                        endereco = tds[1].get_text(strip=True) if len(tds) > 1 else ""
                        cidade_row = tds[2].get_text(strip=True) if len(tds) > 2 else ""
                        
                        if not id_imovel or not endereco:
                            continue
                        
                        imovel = {
                            'id': id_imovel,
                            'endereco': endereco,
                            'cidade': cidade_row,
                            'estado': estado,
                            'tipo': 'imovel'
                        }
                        
                        imoveis.append(imovel)
                        
                    except Exception as e:
                        logger.debug(f"Erro na linha: {e}")
                        continue
            
            browser.close()
            
            logger.info(f"✅ {len(imoveis)} imóveis encontrados!")
            
    except Exception as e:
        logger.error(f"❌ Erro no scraping: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    return imoveis

