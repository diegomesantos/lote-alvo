"""
Scraper com Playwright para leilões de imóveis da Caixa Econômica Federal
Contorna bloqueios contra bots simulando navegador real + espera de AJAX

URL: https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis
"""

import logging
from decimal import Decimal
from datetime import datetime
import asyncio
from playwright.async_api import async_playwright
import re

logger = logging.getLogger(__name__)


class CaixaLeiloeScraperPlaywright:
    """Scraper com Playwright para leilões da Caixa Econômica"""

    BASE_URL = "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis"

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
    async def buscar_imoveis_async(estado, cidade=None, modalidade='14'):
        """
        Busca imóveis usando Playwright (navegador real com AJAX)

        Args:
            estado: Sigla do estado (SP, RJ, BA, etc)
            cidade: Nome da cidade (opcional)
            modalidade: Tipo de modalidade (14=Leilão SFI, etc)

        Returns:
            Lista de imóveis encontrados
        """
        imoveis = []

        async with async_playwright() as p:
            # Abre navegador em modo headless
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()

            try:
                logger.info(f"🌐 Abrindo página da Caixa para {estado}...")
                await page.goto(CaixaLeiloeScraperPlaywright.BASE_URL, wait_until='load', timeout=45000)

                # Aguarda formulário carregar
                logger.info("⏳ Aguardando formulário carregar...")
                # O formulário pode estar em um iframe
                try:
                    await page.wait_for_selector('#cmb_estado', timeout=10000)
                    logger.info("✓ Formulário encontrado na página principal")
                except:
                    # Procura por iframe
                    logger.info("Procurando formulário em iframes...")
                    iframes = await page.query_selector_all('iframe')
                    logger.info(f"  Iframes encontrados: {len(iframes)}")

                    for idx, iframe in enumerate(iframes):
                        try:
                            frame = await iframe.content_frame()
                            if frame:
                                # Tenta encontrar cmb_estado dentro do iframe
                                elemento = await frame.query_selector('#cmb_estado')
                                if elemento:
                                    logger.info(f"✓ Formulário encontrado no iframe {idx}")
                                    # Aguarda um pouco para o iframe estar pronto
                                    await page.wait_for_timeout(1000)
                                    break
                        except:
                            continue

                await page.wait_for_timeout(1000)

                # Seleciona o estado
                logger.info(f"📍 Selecionando estado {estado}...")
                estado_upper = estado.upper()

                # Muda o valor do select
                await page.select_option('#cmb_estado', estado_upper)
                await page.wait_for_timeout(500)

                # Dispara o evento onChange para carregar cidades
                await page.evaluate("document.getElementById('cmb_estado').onchange()")
                await page.wait_for_timeout(1000)

                # Aguarda a requisição AJAX de cidades
                logger.info(f"⏳ Aguardando cidades carregarem via AJAX...")
                try:
                    # Aguarda resposta da requisição de cidades
                    await page.wait_for_response(
                        lambda resp: 'carregaListaCidades.asp' in resp.url and resp.status == 200,
                        timeout=10000
                    )
                except:
                    logger.warning("Timeout na resposta AJAX de cidades, continuando...")

                await page.wait_for_timeout(1500)

                # Verifica quantas cidades estão disponíveis
                cidades_options = await page.locator('#cmb_cidade option').all()
                logger.info(f"✓ {len(cidades_options)} opções de cidades disponíveis")

                # Se houver cidades e foi especificada uma, tenta selecionar
                if cidade and len(cidades_options) > 1:
                    logger.info(f"🏙️ Buscando cidade '{cidade}'...")
                    try:
                        # Obtém lista de cidades disponíveis
                        for option in cidades_options:
                            option_value = await option.get_attribute('value')
                            option_text = await option.text_content()

                            if cidade.upper() in (option_text.upper() if option_text else ''):
                                logger.info(f"  → Encontrada: {option_text}")
                                await page.select_option('#cmb_cidade', option_value)
                                await page.wait_for_timeout(500)
                                break
                        else:
                            logger.warning(f"  Cidade '{cidade}' não encontrada, buscando todo o estado")
                    except Exception as city_error:
                        logger.warning(f"Erro ao selecionar cidade: {str(city_error)}")

                # Aguarda mais um pouco para JavaScript processar
                await page.wait_for_timeout(2000)

                # Clica no botão de busca
                logger.info("🔍 Clicando em buscar...")
                botao_found = False

                # Tenta diferentes seletores para o botão
                for selector in ['button:has-text("Buscar")', 'button:has-text("Pesquisar")', 'input[type="submit"]', 'button[type="submit"]']:
                    try:
                        botao = await page.query_selector(selector)
                        if botao:
                            await botao.click()
                            botao_found = True
                            logger.info(f"  ✓ Botão clicado: {selector}")
                            break
                    except:
                        continue

                if not botao_found:
                    logger.warning("Botão de busca não encontrado, tentando via JavaScript")
                    # Tenta chamar a função JavaScript diretamente
                    await page.evaluate("if(typeof carregaPesquisaImoveis === 'function') carregaPesquisaImoveis();")

                # Aguarda resultados carregarem
                logger.info("⏳ Aguardando resultados...")
                await page.wait_for_timeout(3000)

                # Tenta múltiplas vezes verificar se há resultados
                for attempt in range(5):
                    try:
                        # Procura pela tabela de resultados
                        tabela = await page.query_selector('table tbody')
                        if tabela:
                            logger.info(f"✓ Tabela de resultados encontrada na tentativa {attempt + 1}")
                            break
                    except:
                        pass

                    if attempt < 4:
                        await page.wait_for_timeout(1000)

                # Extrai dados dos imóveis
                logger.info("📊 Extraindo dados dos imóveis...")
                imoveis = await CaixaLeiloeScraperPlaywright._extrair_imoveis_playwright(page)

                logger.info(f"✅ {len(imoveis)} imóveis encontrados em {estado}")

            except Exception as e:
                logger.error(f"❌ Erro durante scraping: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

            finally:
                await browser.close()

        return imoveis

    @staticmethod
    async def _extrair_imoveis_playwright(page):
        """
        Extrai dados de imóveis da página com múltiplas estratégias
        """
        imoveis = []

        try:
            logger.info("Tentando extrair de tabela HTML...")
            # Procura pela tabela
            linhas = await page.query_selector_all('table tbody tr')
            logger.info(f"  Encontradas {len(linhas)} linhas na tabela")

            if not linhas:
                logger.info("Tentando estrutura alternativa (divs)...")
                linhas = await page.query_selector_all('[class*="imovel"], [class*="resultado"]')
                logger.info(f"  Encontradas {len(linhas)} divs")

            for idx, linha in enumerate(linhas):
                try:
                    # Extrai todas as células
                    tds = await linha.query_selector_all('td')

                    if len(tds) >= 3:
                        # Extrai texto de cada célula
                        tds_text = []
                        for td in tds:
                            text = await td.text_content()
                            # Remove espaços em branco extras
                            cleaned_text = text.strip() if text else ''
                            # Remove quebras de linha e espaços múltiplos
                            cleaned_text = ' '.join(cleaned_text.split())
                            tds_text.append(cleaned_text)

                        # Monta dict do imóvel com validação
                        if len(tds_text) >= 3 and tds_text[0] and tds_text[1]:
                            imovel = {
                                'id': tds_text[0],
                                'endereco': tds_text[1],
                                'cidade': tds_text[2] if len(tds_text) > 2 else '',
                                'tipo': tds_text[3] if len(tds_text) > 3 else '',
                                'valor': tds_text[4] if len(tds_text) > 4 else '0',
                            }

                            imoveis.append(imovel)
                            logger.debug(f"  Imóvel {idx + 1}: {imovel['endereco'][:50]}")

                except Exception as e:
                    logger.debug(f"  Erro ao extrair linha {idx}: {str(e)}")
                    continue

            # Se não encontrou, tenta extrair do conteúdo de texto
            if not imoveis:
                logger.info("Nenhum imóvel extraído via tabela, tentando extração alternativa...")
                try:
                    # Obtém todo o texto da página
                    texto = await page.text_content('body')

                    # Procura por padrões de endereço (simplista)
                    if 'Avenida' in texto or 'Rua' in texto or 'Logradouro' in texto:
                        logger.info("  Padrões de endereço encontrados na página")
                        logger.info(f"  Primeira 200 chars: {texto[:200]}")
                    else:
                        logger.warning("  Nenhum padrão de endereço encontrado")

                except Exception as e:
                    logger.warning(f"  Erro na extração alternativa: {str(e)}")

        except Exception as e:
            logger.error(f"Erro geral ao extrair imóveis: {str(e)}")

        return imoveis

    @staticmethod
    def buscar_imoveis(estado, cidade=None):
        """
        Wrapper síncrono para buscar imóveis
        """
        try:
            # Obtém ou cria event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            imoveis = loop.run_until_complete(
                CaixaLeiloeScraperPlaywright.buscar_imoveis_async(estado, cidade)
            )
            return imoveis
        except Exception as e:
            logger.error(f"Erro ao buscar imóveis: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    @staticmethod
    def normalizar_imovel(imovel_data):
        """
        Normaliza dados do imóvel para formato padrão
        """
        try:
            # Extrai valor numérico
            valor_str = str(imovel_data.get('valor', '0')).replace('R$', '').replace('.', '').replace(',', '.')

            # Remove caracteres não numéricos
            valor_limpo = re.sub(r'[^\d.]', '', valor_str)
            valor = Decimal(valor_limpo) if valor_limpo else Decimal(0)

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


def buscar_leiloes_caixa_pw(estado, cidade=None):
    """
    Função simplificada para buscar leilões com Playwright

    Usage:
        imoveis = buscar_leiloes_caixa_pw('SP')
        imoveis = buscar_leiloes_caixa_pw('SP', 'São Paulo')
    """
    scraper = CaixaLeiloeScraperPlaywright()
    imoveis_raw = scraper.buscar_imoveis(estado, cidade)

    # Normaliza cada imóvel
    imoveis = []
    for imovel_raw in imoveis_raw:
        imovel_normalizado = scraper.normalizar_imovel(imovel_raw)
        if imovel_normalizado:
            imoveis.append(imovel_normalizado)

    return imoveis
