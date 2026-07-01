"""
Tabelas de emolumentos de Escritura e Registro de Imóveis por estado.
Fonte: Tribunais de Justiça Estaduais — tabelas 2025/2026
Valores são estimativas; confirme sempre com o cartório competente.

Estrutura de cada tabela:
  Lista de tuplas (limite_superior, valor_fixo)
  O último item tem limite_superior = float('inf')
  A lógica é: se base <= limite, usa esse valor fixo.
"""
from datetime import date

# ─── Bahia (BA) — TJ-BA 2026 ────────────────────────────────────────────────
# Fonte: Tabela de Custas TJBA 2026 (Decreto). Item I (Notas) e Item VII
# (Registro de Imóveis) têm faixas e valores idênticos, então usamos a mesma
# tabela para escritura e registro.
TABELA_BA = [
    (1_600.00,       333.34),
    (3_200.00,       419.30),
    (8_000.00,       505.24),
    (12_000.00,      546.06),
    (16_000.00,      587.62),
    (24_000.00,      670.86),
    (32_000.00,      756.26),
    (47_000.00,      835.36),
    (63_000.00,      920.54),
    (78_000.00,    1_010.84),
    (118_000.00,   1_076.62),
    (160_000.00,   1_164.82),
    (235_000.00,   1_885.66),
    (350_000.00,   2_828.84),
    (530_000.00,   4_248.68),
    (800_000.00,   6_371.40),
    (1_200_000.00, 9_555.60),
    (1_800_000.00,11_466.66),
    (2_700_000.00,14_907.00),
    (4_000_000.00,19_379.08),
    (float('inf'),25_192.90),
]

# ─── São Paulo (SP) — TJ-SP 2026 ────────────────────────────────────────────
# Registro de imóveis e escritura têm tabelas distintas no TJ-SP.
# Escritura = Tabela Tabelionato de Notas (CNB/SP, "Capital 2026"), item 1
# "Escritura com valor declarado", coluna TOTAL (emolumento + estado + ISS +
# fundos). Faixas com limites em múltiplos de UFESP, como na fonte oficial.
TABELA_SP_ESCRITURA = [
    (1_524.00,        356.90),
    (5_761.00,        533.35),
    (9_603.00,        832.77),
    (19_210.00,     1_189.68),
    (38_420.00,     1_608.08),
    (76_840.00,     1_907.60),
    (115_260.00,    2_264.49),
    (153_680.00,    2_682.90),
    (192_100.00,    3_039.89),
    (230_520.00,    3_400.86),
    (268_940.00,    3_815.19),
    (307_360.00,    4_176.24),
    (330_146.00,    4_594.65),
    (384_200.00,    4_890.01),
    (768_400.00,    5_427.43),
    (1_152_600.00,  6_026.36),
    (1_536_800.00,  6_682.74),
    (2_345_066.00,  7_384.26),
    (3_908_444.00, 10_255.96),
    (5_862_665.00, 13_332.69),
    (7_816_887.00, 16_409.51),
    (9_771_109.00, 19_486.25),
    (float('inf'), 65_637.95),
]

# Registro de Imóveis = Tabela III.B do TJ-SP 2026 (coluna TOTAL: emolumentos +
# FUNJECC + FUNADEP + FEADMP + ISS 5% + selos). Faixas representativas extraídas
# da tabela oficial (faixas redondas de R$); valores TOTAL exatos da fonte.
TABELA_SP_REGISTRO = [
    (5_000.00,        107.82),
    (10_000.00,       189.52),
    (20_000.00,       351.74),
    (30_000.00,       511.78),
    (50_000.00,       836.31),
    (75_000.00,     1_320.86),
    (100_000.00,    1_806.52),
    (120_000.00,    1_967.74),
    (150_000.00,    2_209.38),
    (200_000.00,    2_545.11),
    (250_000.00,    2_869.64),
    (300_000.00,    3_462.74),
    (350_000.00,    3_576.93),
    (400_000.00,    3_691.11),
    (450_000.00,    3_805.19),
    (500_000.00,    3_919.38),
    (600_000.00,    3_976.43),
    (700_000.00,    4_033.47),
    (800_000.00,    4_090.06),
    (1_000_000.00,  4_204.69),
    (2_000_000.00,  4_261.84),
    (3_000_000.00,  4_318.87),
    (5_000_000.00,  4_433.06),
    (9_000_000.00,  4_547.15),
    (float('inf'),  4_615.37),
]

# ─── Rio de Janeiro (RJ) — TJ-RJ 2026 ───────────────────────────────────────
# Fonte: TJ-RJ, Lei 9.873/22 / tabela 2026 (DJe 30/12/2025), item "1 - Escritura
# com valor declarado". Os valores já são o TOTAL ao usuário = emolumento-base ×
# 1,38, pois sobre o emolumento incidem os acréscimos legais confirmados na
# própria portaria (e conferidos no exemplo numérico dela): 20% FETJ + 5% FUNPERJ
# + 5% FUNDPERJ + 6% FUNARPEN + 2% PMCMV = 38%. Acima de R$ 561.712 vale a
# fórmula da fonte: +R$ 252,43 de emolumento por faixa de R$ 140.427,98 (aqui já
# ×1,38). NÃO inclui o ISS municipal (varia por município, ~2-5%). A tabela de
# Registro de Imóveis está em publicação separada; aqui a de Notas é usada também
# como aproximação para registro.
TABELA_RJ = [
    (21_064.17,       458.02),
    (42_128.37,       756.86),
    (63_192.57,     1_055.76),
    (84_256.79,     1_294.78),
    (112_342.37,    2_294.98),
    (140_427.98,    2_709.37),
    (280_855.98,    3_665.62),
    (561_711.99,    3_933.30),
    (702_139.98,    4_281.66),
    (842_567.96,    4_630.01),
    (982_995.94,    4_978.36),
    (1_123_423.92,  5_326.72),
    (1_263_851.90,  5_675.07),
    (1_404_279.88,  6_023.42),
    (1_544_707.86,  6_371.78),
    (1_685_135.84,  6_720.13),
    (1_825_563.82,  7_068.48),
    (1_965_991.80,  7_416.84),
    (2_246_847.76,  8_113.54),
    (2_527_703.72,  8_810.25),
    (2_808_559.68,  9_506.96),
    (float('inf'),  9_855.31),
]

# ─── Minas Gerais (MG) — TJ-MG 2026 ─────────────────────────────────────────
# Fonte: Portaria CGJ/MG 8664/2025 (valores 2026), Lei estadual 15.424/2004.
# Escritura (Tabela 1, item 4.b) e Registro (Tabela 4, item 5.e) têm a MESMA
# tabela. Coluna "Valor Final ao Usuário" (emolumento + Taxa de Fiscalização
# Judiciária). Acima de R$ 3.200.000 a fonte usa fórmula (nota XVII): o teto
# aqui subestima levemente valores muito altos.
TABELA_MG = [
    (1_400.00,        220.55),
    (2_720.00,        359.76),
    (5_440.00,        521.35),
    (7_000.00,        721.75),
    (14_000.00,       962.47),
    (28_000.00,     1_243.47),
    (42_000.00,     1_564.07),
    (56_000.00,     1_925.31),
    (70_000.00,     2_326.51),
    (105_000.00,    2_928.06),
    (140_000.00,    3_721.52),
    (175_000.00,    3_979.69),
    (210_000.00,    4_238.32),
    (280_000.00,    4_772.07),
    (350_000.00,    4_903.53),
    (420_000.00,    5_035.59),
    (560_000.00,    5_523.14),
    (700_000.00,    5_826.70),
    (840_000.00,    6_130.87),
    (1_120_000.00,  6_866.53),
    (1_400_000.00,  7_437.64),
    (1_680_000.00,  8_009.72),
    (3_200_000.00,  8_582.97),
    (float('inf'),  8_582.97),
]

# ─── Paraná (PR) — TJ-PR 2026 ────────────────────────────────────────────────
# Fonte: TJ-PR, Lei 6.149/1970 + anexo atualizado (Tabela XI item IV - Notas;
# Tabela XIII item b - Registro de Imóveis; mesma tabela para escritura e
# registro). Emolumento em R$ por faixa de valor (a fonte usa VRCext = R$ 0,277;
# aqui já convertido para reais). A tabela "não é progressiva": acima de
# R$ 62.602 o emolumento fica no teto de R$ 1.377,24. O FUNREJUS (0,2%) é somado
# à parte como regra extra — é uma APROXIMAÇÃO, pois a tabela própria do fundo
# está em legislação separada (não consta deste anexo). Conferir o FUNREJUS.
TABELA_PR = [
    (15_512.00,       349.02),
    (18_282.00,       411.34),
    (21_052.00,       473.67),
    (23_822.00,       535.99),
    (26_592.00,       598.32),
    (29_362.00,       660.64),
    (32_132.00,       722.97),
    (34_902.00,       785.29),
    (37_672.00,       847.62),
    (40_442.00,       909.94),
    (43_212.00,       972.27),
    (45_982.00,     1_011.60),
    (48_752.00,     1_072.54),
    (51_522.00,     1_133.48),
    (54_292.00,     1_194.42),
    (57_062.00,     1_255.36),
    (59_832.00,     1_316.30),
    (62_602.00,     1_377.24),
    (float('inf'),  1_377.24),
]
PR_FUNREJUS_PCT = 0.002  # 0,2% (aproximação — ver nota acima)

# ─── Rio Grande do Sul (RS) — TJ-RS 2026 (índice IPC/IEPE/UFRGS +5,86%) ──────
# Fonte: TJ-RS, Tabela de Emolumentos 2026 (Lei estadual 12.692/06), vigência
# 01/01/2026. Escritura (Tabelionato de Notas, item 1.i "escrituras com
# conteúdo financeiro") e Registro de Imóveis (item 1) têm tabelas DISTINTAS.
# Emolumento puro (RS não tem pilha de fundos; só o selo digital fixo à parte).
TABELA_RS_ESCRITURA = [
    (2_481.80,        222.80),
    (7_445.20,        252.50),
    (12_408.70,       292.40),
    (24_816.80,       395.60),
    (49_633.80,       552.70),
    (74_451.00,       628.70),
    (99_267.80,       728.60),
    (148_901.60,      928.10),
    (198_535.70,    1_076.70),
    (248_169.50,    1_277.10),
    (297_803.60,    1_475.80),
    (347_437.30,    1_675.30),
    (446_705.00,    2_075.00),
    (496_338.90,    2_274.40),
    (595_606.80,    2_673.20),
    (744_508.50,    3_271.90),
    (992_677.90,    3_870.10),
    (1_240_847.60,  4_867.50),
    (float('inf'),  5_482.90),
]
TABELA_RS_REGISTRO = [
    (2_481.80,        226.10),
    (7_445.20,        241.00),
    (12_408.70,       260.90),
    (24_816.80,       310.40),
    (49_633.80,       390.80),
    (74_451.00,       465.90),
    (99_267.80,       565.50),
    (148_901.60,      764.70),
    (198_535.70,      964.20),
    (248_169.50,    1_163.90),
    (297_803.60,    1_313.30),
    (347_437.30,    1_512.30),
    (446_705.00,    1_911.30),
    (496_338.90,    2_111.70),
    (620_424.00,    2_460.80),
    (744_508.50,    2_958.90),
    (992_677.90,    3_956.20),
    (1_240_847.60,  4_953.60),
    (float('inf'),  5_482.90),
]

# ─── Pernambuco (PE) — TJ-PE 2026 ────────────────────────────────────────────
# Fonte: TJ-PE, Ato 1556/2025 (DJe 390, 18/12/2025), valores 2026 (+4,46% IPCA).
# Escritura = Tabela 'D' item I; Registro = Tabela 'E' item IV (ambos "com
# conteúdo financeiro"). São EMOLUMENTOS apenas — a TSNR (Taxa de Serviço
# Notarial e de Registro) e fundos são cobrados à parte e NÃO estão somados
# aqui, então o custo real ao usuário é um pouco maior. Escritura teto
# R$ 7.084,10; registro teto R$ 4.723,28.
TABELA_PE_ESCRITURA = [
    (1_000.00,        237.84),
    (5_000.00,        399.50),
    (15_000.00,       722.80),
    (30_000.00,     1_126.92),
    (50_000.00,     1_773.53),
    (70_000.00,     2_420.11),
    (90_000.00,     3_066.78),
    (110_000.00,    3_713.32),
    (130_000.00,    4_359.98),
    (150_000.00,    5_006.54),
    (175_000.00,    5_814.82),
    (200_000.00,    6_623.08),
    (210_000.00,    6_946.38),
    (float('inf'),  7_084.10),
]
TABELA_PE_REGISTRO = [
    (5_000.00,        237.84),
    (10_000.00,       399.50),
    (20_000.00,       561.13),
    (35_000.00,       763.22),
    (50_000.00,     1_005.73),
    (75_000.00,     1_409.82),
    (100_000.00,    1_813.99),
    (130_000.00,    2_298.89),
    (160_000.00,    2_783.87),
    (200_000.00,    3_430.47),
    (240_000.00,    4_077.07),
    (278_000.00,    4_707.48),
    (float('inf'),  4_723.28),
]

# ─── Ceará (CE) — TJ-CE 2026 ──────────────────────────────────────────────────
# ⚠️ PENDENTE DE VALIDAÇÃO. Fonte oficial 2026 (Portaria 2982/2025,
# portal.tjce.jus.br/uploads/2026/01/Tab.-Emolumentos-2026.pdf, +4,46% UFIRCE).
# OCR da tabela renderizada recupera as faixas mescladas (cód. 002008-002017),
# mas a estrutura é ambígua e arriscada: faixas pequenas (R$ 104 a R$ 23.322,
# unidade não clara — provavelmente UFIRCE), variantes "dentro/fora do
# município" e teto em "acima de R$ 23.322,58". O OCR ainda perde dígitos/
# códigos. Não foi possível extrair valores confiáveis; manter pendente e
# atualizar manualmente conferindo a tabela oficial. Números abaixo são legados.
TABELA_CE = [
    (2_000.00,        196.56),
    (4_000.00,        247.28),
    (8_000.00,        311.57),
    (16_000.00,       392.52),
    (24_000.00,       494.58),
    (40_000.00,       623.12),
    (60_000.00,       785.14),
    (80_000.00,       989.21),
    (120_000.00,    1_246.52),
    (160_000.00,    1_571.01),
    (240_000.00,    1_980.37),
    (320_000.00,    2_495.34),
    (480_000.00,    3_144.33),
    (float('inf'),  3_961.72),
]

# ─── Distrito Federal (DF) — TJDFT 2026 ──────────────────────────────────────
# Fonte: TJDFT, Resolução 2 de 19/12/2025 (+4,87% IPCA), tabela completa 2026.
# Coluna "TOTAL" (emolumento + FUNDESP + ISSQN). Escritura (Tabela I, item 1
# "Escrituras com conteúdo econômico") e Registro de Imóveis têm tabelas
# DISTINTAS, em faixas de múltiplos da UF-DF.
TABELA_DF_ESCRITURA = [
    (9_524.89,        439.30),
    (15_272.67,       667.72),
    (28_738.89,     1_370.60),
    (57_477.78,     1_845.04),
    (85_888.21,     1_932.90),
    (200_351.09,    2_020.76),
    (343_224.42,    2_196.48),
    (858_882.16,    2_372.20),
    (1_313_777.69,  2_547.92),
    (1_806_444.32,  2_723.63),
    (float('inf'),  2_899.35),
]
TABELA_DF_REGISTRO = [
    (32_844.44,       701.11),
    (82_111.11,       885.62),
    (164_222.21,    1_070.12),
    (262_755.54,    1_199.28),
    (574_777.74,    1_383.78),
    (870_377.72,    1_568.29),
    (1_149_555.47,  1_752.80),
    (1_477_999.89,  1_937.29),
    (1_970_666.52,  2_121.80),
    (float('inf'),  2_306.30),
]

# ─── Santa Catarina (SC) — TJ-SC 2026 ─────────────────────────────────────────
# Fonte: TJ-SC, LC 755/2019 (alt. LC 846/2023), Circular CGJ 643/2025, valores
# 2026. Coluna "Total (R$)" (emolumento + FRJ + selo) da Tabela III, item 2.2
# (Registro com valor). Valores de REGISTRO de imóveis, usados também como
# aproximação para escritura (a tabela do Tabelião de Notas não constava desta
# fonte; conferir a escritura separadamente se precisar de mais precisão).
TABELA_SC = [
    (13_786.59,       207.75),
    (35_845.12,       438.45),
    (53_767.69,       660.32),
    (79_962.21,     1_024.85),
    (100_642.09,    1_290.76),
    (158_545.76,    1_961.70),
    (212_313.47,    2_525.19),
    (326_100.05,    2_799.08),
    (426_100.05,    2_926.81),
    (526_100.05,    3_054.54),
    (726_100.05,    3_310.00),
    (1_026_100.05,  3_693.19),
    (1_526_100.05,  4_331.84),
    (2_026_100.05,  4_970.49),
    (float('inf'),  7_141.90),
]

# ─── Goiás (GO) — TJ-GO 2026 ───────────────────────────────────────────────────
# Fonte: TJ-GO, Provimento Conjunto 179/2025 (valores 2026, +4,46%), Lei
# 19.191/2015. Escritura = Tabela XIII, item 63.A (sobre o valor econômico);
# Registro = Tabela XIV, item 76. Emolumento por faixa (FUNDESP/selo à parte).
TABELA_GO_ESCRITURA = [
    (653.80,          111.35),
    (1_307.62,        168.88),
    (2_615.24,        228.27),
    (5_230.47,        319.17),
    (10_460.94,       636.51),
    (15_691.43,       681.04),
    (26_152.37,       862.90),
    (39_228.54,     1_091.15),
    (52_304.74,     1_456.73),
    (65_380.92,     1_729.50),
    (104_609.47,    2_273.23),
    (156_914.21,    3_408.91),
    (261_523.68,    4_166.03),
    (392_285.51,    4_923.17),
    (523_047.35,    5_680.28),
    (float('inf'),  6_062.56),
]
TABELA_GO_REGISTRO = [
    (653.80,           61.56),
    (1_307.62,         93.32),
    (2_615.24,        119.13),
    (5_230.47,        172.76),
    (10_460.94,       339.54),
    (15_691.43,       363.35),
    (26_152.37,       462.64),
    (39_228.54,       585.76),
    (52_304.74,       776.37),
    (65_380.92,       923.29),
    (104_609.47,    1_294.60),
    (156_914.21,    1_945.88),
    (261_523.68,    2_620.98),
    (392_285.51,    3_441.04),
    (523_047.35,    4_054.59),
    (784_571.03,    4_866.70),
    (1_176_856.54,  5_831.70),
    (1_569_142.07,  6_780.81),
    (float('inf'),  7_407.33),
]

# ─── Espírito Santo (ES) — TJ-ES 2026 ──────────────────────────────────────────
# Fonte: TJ-ES, Ato CGJ-ES 10/2025 (vigência 01/01/2026; ES reajustou após ficar
# parado desde 2001). A tabela oficial só existe como IMAGEM; estes valores foram
# extraídos por OCR da tabela de Registro de Imóveis 2026 (com ISS) publicada por
# cartório do ES. Coluna VALOR (total ao usuário), teto R$ 5.981,93 acima de
# R$ 200.000. As faixas 60k-80k seguem o incremento constante da tabela
# (+R$ 139,02/5k, conferido contra a faixa seguinte). Usada também como
# aproximação para escritura (a tabela de Notas 2026 não está disponível em
# texto). NÃO há parser automático: OCR de imagem é frágil para auto-aplicar;
# revalidar manualmente quando o TJ-ES publicar a tabela em texto.
TABELA_ES = [
    (1_000.00,        171.05),
    (3_000.00,        198.84),
    (5_000.00,        254.45),
    (10_000.00,       351.75),
    (15_000.00,       490.78),
    (20_000.00,       629.83),
    (25_000.00,       768.80),
    (30_000.00,       907.83),
    (35_000.00,     1_046.86),
    (40_000.00,     1_185.84),
    (45_000.00,     1_324.88),
    (50_000.00,     1_463.90),
    (55_000.00,     1_602.90),
    (60_000.00,     1_741.92),
    (65_000.00,     1_880.94),
    (70_000.00,     2_019.96),
    (75_000.00,     2_158.98),
    (80_000.00,     2_298.00),
    (85_000.00,     2_437.00),
    (90_000.00,     2_576.02),
    (95_000.00,     2_715.07),
    (100_000.00,    2_854.05),
    (105_000.00,    2_993.06),
    (110_000.00,    3_132.12),
    (115_000.00,    3_271.09),
    (120_000.00,    3_410.13),
    (125_000.00,    3_549.14),
    (130_000.00,    3_688.14),
    (140_000.00,    3_896.72),
    (150_000.00,    4_174.73),
    (160_000.00,    4_452.74),
    (170_000.00,    4_730.80),
    (180_000.00,    5_008.83),
    (200_000.00,    5_425.88),
    (float('inf'),  5_981.93),
]

# ─── Índice geral de estados disponíveis ────────────────────────────────────
# Para estados não cobertos, usamos uma estimativa genérica (0.5% do valor)
ESTADOS_DISPONIVEIS = {
    "BA": {"escritura": TABELA_BA,    "registro": TABELA_BA,    "extra": None},
    "SP": {"escritura": TABELA_SP_ESCRITURA, "registro": TABELA_SP_REGISTRO, "extra": None},
    "RJ": {"escritura": TABELA_RJ,    "registro": TABELA_RJ,    "extra": None},
    "MG": {"escritura": TABELA_MG,    "registro": TABELA_MG,    "extra": None},
    "PR": {"escritura": TABELA_PR,    "registro": TABELA_PR,    "extra": ("FUNREJUS", PR_FUNREJUS_PCT)},
    "RS": {"escritura": TABELA_RS_ESCRITURA, "registro": TABELA_RS_REGISTRO, "extra": None},
    "PE": {"escritura": TABELA_PE_ESCRITURA, "registro": TABELA_PE_REGISTRO, "extra": None},
    "CE": {"escritura": TABELA_CE,    "registro": TABELA_CE,    "extra": None},
    "DF": {"escritura": TABELA_DF_ESCRITURA, "registro": TABELA_DF_REGISTRO, "extra": None},
    "SC": {"escritura": TABELA_SC,    "registro": TABELA_SC,    "extra": None},
    "GO": {"escritura": TABELA_GO_ESCRITURA, "registro": TABELA_GO_REGISTRO, "extra": None},
    "ES": {"escritura": TABELA_ES,    "registro": TABELA_ES,    "extra": None},
}

LISTA_ESTADOS = sorted(ESTADOS_DISPONIVEIS.keys())

ESTADOS_NOMES = {
    "AC":"Acre","AL":"Alagoas","AM":"Amazonas","AP":"Amapá","BA":"Bahia",
    "CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás",
    "MA":"Maranhão","MG":"Minas Gerais","MS":"Mato Grosso do Sul",
    "MT":"Mato Grosso","PA":"Pará","PB":"Paraíba","PE":"Pernambuco",
    "PI":"Piauí","PR":"Paraná","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte",
    "RO":"Rondônia","RR":"Roraima","RS":"Rio Grande do Sul",
    "SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins",
}

TODOS_ESTADOS = sorted(ESTADOS_NOMES.keys())


def _hoje():
    return date.today()


def _vigente_qs(queryset, data_referencia):
    from django.db.models import Q

    return queryset.filter(
        ativo=True,
        vigente_inicio__lte=data_referencia,
    ).filter(
        Q(vigente_fim__isnull=True) | Q(vigente_fim__gte=data_referencia)
    )


def _buscar_tabela_db(uf, tipo, data_referencia=None):
    data_referencia = data_referencia or _hoje()
    try:
        from django.db.utils import OperationalError, ProgrammingError
        from apps.calculadora.models import CartorioTabela

        queryset = CartorioTabela.objects.filter(uf=uf, tipo=tipo)
        return (
            _vigente_qs(queryset, data_referencia)
            .prefetch_related("faixas")
            .order_by("-vigente_inicio", "-ano", "-id")
            .first()
        )
    except (ImportError, OperationalError, ProgrammingError):
        return None


def _buscar_extra_db(uf, data_referencia=None):
    data_referencia = data_referencia or _hoje()
    try:
        from django.db.utils import OperationalError, ProgrammingError
        from apps.calculadora.models import CartorioRegraExtra

        queryset = CartorioRegraExtra.objects.filter(uf=uf)
        return (
            _vigente_qs(queryset, data_referencia)
            .order_by("-vigente_inicio", "-ano", "-id")
            .first()
        )
    except (ImportError, OperationalError, ProgrammingError):
        return None


def _tabela_db_para_tuplas(tabela):
    if not tabela:
        return None
    faixas = list(tabela.faixas.all().order_by("ordem"))
    if not faixas:
        return None
    return [
        (
            float("inf") if faixa.limite_superior is None else float(faixa.limite_superior),
            float(faixa.valor),
        )
        for faixa in faixas
    ]


def _fonte_tabela(tabela):
    if not tabela:
        return None
    return {
        "uf": tabela.uf,
        "ano": tabela.ano,
        "tipo": tabela.tipo,
        "status": tabela.status,
        "fonte_nome": tabela.fonte_nome,
        "fonte_url": tabela.fonte_url,
        "fundamento": tabela.fundamento,
        "vigencia": tabela.vigente_label,
    }


def _fonte_extra(extra):
    if not extra:
        return None
    return {
        "uf": extra.uf,
        "ano": extra.ano,
        "tipo": "extra",
        "status": extra.status,
        "fonte_nome": extra.fonte_nome,
        "fonte_url": extra.fonte_url,
        "fundamento": extra.fundamento,
        "vigencia": extra.vigente_label,
        "nome": extra.nome,
    }


def _calcular_cartorio_db(estado, base, tipo_leilao="Extrajudicial", data_referencia=None):
    uf = estado.upper() if estado else "BA"
    tabela_registro = _buscar_tabela_db(uf, "registro", data_referencia)
    tab_registro = _tabela_db_para_tuplas(tabela_registro)
    if not tab_registro:
        return None

    tabela_escritura = None
    tab_escritura = None
    if tipo_leilao != "Judicial":
        tabela_escritura = _buscar_tabela_db(uf, "escritura", data_referencia)
        tab_escritura = _tabela_db_para_tuplas(tabela_escritura)
        if not tab_escritura:
            return None

    if tipo_leilao == "Judicial":
        escritura_val = 0
        escritura_faixa = "Carta de arrematação (isenta de escritura pública)"
    else:
        escritura_val, escritura_faixa, _ = buscar_faixa(tab_escritura, base)

    registro_val, registro_faixa, _ = buscar_faixa(tab_registro, base)

    extra = _buscar_extra_db(uf, data_referencia)
    extra_val = 0
    extra_nome = None
    if extra:
        extra_nome = extra.nome
        extra_val = base * float(extra.percentual) / 100

    fontes = [
        fonte for fonte in (
            _fonte_tabela(tabela_escritura),
            _fonte_tabela(tabela_registro),
            _fonte_extra(extra),
        )
        if fonte
    ]
    fonte_principal = fontes[0] if fontes else {}
    status_pendente = any(fonte.get("status") == "pendente_validacao" for fonte in fontes)
    aviso = None
    if status_pendente:
        aviso = "Tabela cartorária versionada pendente de validação formal da fonte oficial."

    return dict(
        escritura=escritura_val,
        registro=registro_val,
        extra=extra_val,
        extra_nome=extra_nome,
        total=escritura_val + registro_val + extra_val,
        escritura_faixa=escritura_faixa,
        registro_faixa=registro_faixa,
        aviso=aviso,
        origem="banco",
        fonte_nome=fonte_principal.get("fonte_nome", ""),
        fonte_url=fonte_principal.get("fonte_url", ""),
        fonte_ano=fonte_principal.get("ano"),
        fonte_status=fonte_principal.get("status", ""),
        fonte_vigencia=fonte_principal.get("vigencia", ""),
        fontes=fontes,
    )


def obter_tabelas_cartorio(estado, tipo_leilao="Extrajudicial", data_referencia=None):
    """Retorna tabelas para exibição, preferindo dados versionados do banco."""
    uf = estado.upper() if estado else "BA"
    tabela_registro = _buscar_tabela_db(uf, "registro", data_referencia)
    tab_registro = _tabela_db_para_tuplas(tabela_registro)
    tabela_escritura = None
    tab_escritura = None
    if tipo_leilao != "Judicial":
        tabela_escritura = _buscar_tabela_db(uf, "escritura", data_referencia)
        tab_escritura = _tabela_db_para_tuplas(tabela_escritura)

    if tab_registro and (tipo_leilao == "Judicial" or tab_escritura):
        return {
            "escritura": tab_escritura,
            "registro": tab_registro,
            "origem": "banco",
            "fontes": [
                fonte for fonte in (
                    _fonte_tabela(tabela_escritura),
                    _fonte_tabela(tabela_registro),
                )
                if fonte
            ],
        }

    if uf in ESTADOS_DISPONIVEIS:
        dados = ESTADOS_DISPONIVEIS[uf]
        return {
            "escritura": None if tipo_leilao == "Judicial" else dados["escritura"],
            "registro": dados["registro"],
            "origem": "codigo",
            "fontes": [],
        }

    return {"escritura": None, "registro": None, "origem": "estimativa", "fontes": []}


def buscar_faixa(tabela, base):
    """Retorna (valor_emolumento, faixa_texto, indice_faixa)"""
    for i,(limite, valor) in enumerate(tabela):
        if base <= limite:
            limite_ant = tabela[i-1][0] if i > 0 else 0.0
            if limite == float('inf'):
                faixa = f"Acima de R$ {tabela[-2][0]:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            else:
                faixa = f"R$ {limite_ant:,.2f} — R$ {limite:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            return valor, faixa, i
    # fallback: última faixa
    valor = tabela[-1][1]
    faixa = f"Acima de R$ {tabela[-2][0]:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return valor, faixa, len(tabela)-1


def calcular_cartorio(estado, base, tipo_leilao="Extrajudicial"):
    """
    Retorna dict com escritura, registro, extra e total.
    Para leilão judicial extrajudicial, a carta de arrematação substitui a escritura
    mas o registro da carta ainda é necessário (usa tabela de registro).
    """
    uf = estado.upper() if estado else "BA"

    calculo_db = _calcular_cartorio_db(uf, base, tipo_leilao)
    if calculo_db:
        return calculo_db

    if uf in ESTADOS_DISPONIVEIS:
        dados = ESTADOS_DISPONIVEIS[uf]
        tab_escritura = dados["escritura"]
        tab_registro  = dados["registro"]
        extra_info    = dados["extra"]
    else:
        # Estado sem tabela específica: estimativa 0,5% do valor para cada
        val_est = base * 0.005
        return dict(
            escritura=0,           # carta de arrematação dispensada em judicial
            registro=val_est,
            extra=0,
            extra_nome=None,
            total=val_est,
            escritura_faixa="Estimativa (estado sem tabela)",
            registro_faixa="Estimativa (0,5% do valor)",
            aviso=f"⚠️ Tabela oficial de {uf} não disponível. Valores estimados em 0,5%.",
            origem="estimativa",
            fonte_nome="Estimativa interna",
            fonte_url="",
            fonte_ano=None,
            fonte_status="estimativa",
            fonte_vigencia="",
            fontes=[],
        )

    # Escritura: só em compra e venda direta; leilão judicial usa carta de arrematação
    if tipo_leilao == "Judicial":
        escritura_val   = 0
        escritura_faixa = "Carta de arrematação (isenta de escritura pública)"
    else:
        escritura_val, escritura_faixa, _ = buscar_faixa(tab_escritura, base)

    registro_val, registro_faixa, _ = buscar_faixa(tab_registro, base)

    extra_val  = 0
    extra_nome = None
    if extra_info:
        extra_nome = extra_info[0]
        extra_val  = base * extra_info[1]

    total = escritura_val + registro_val + extra_val

    return dict(
        escritura=escritura_val,
        registro=registro_val,
        extra=extra_val,
        extra_nome=extra_nome,
        total=total,
        escritura_faixa=escritura_faixa,
        registro_faixa=registro_faixa,
        aviso=None,
        origem="codigo",
        fonte_nome="Tabela legada do sistema",
        fonte_url="",
        fonte_ano=None,
        fonte_status="legada",
        fonte_vigencia="2025/2026",
        fontes=[],
    )


def tabela_rows_html(tabela, faixa_ativa_idx):
    """Retorna apenas o HTML da tabela (sem wrapper <details>), para uso com st.expander."""
    rows = ""
    for i,(limite, valor) in enumerate(tabela):
        limite_ant = tabela[i-1][0] if i > 0 else 0.0
        if limite == float('inf'):
            faixa_str = f"Acima de R$ {tabela[-2][0]:,.2f}"
        else:
            faixa_str = f"R$ {limite_ant:,.2f} — R$ {limite:,.2f}"
        faixa_str = faixa_str.replace(",","X").replace(".",",").replace("X",".")
        valor_str = f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")
        destaque = ' style="background:#eff6ff;font-weight:700"' if i == faixa_ativa_idx else ""
        badge = ' <span style="font-size:10px;background:#3b82f6;color:#fff;padding:1px 6px;border-radius:99px;margin-left:4px">✓ faixa usada</span>' if i == faixa_ativa_idx else ""
        rows += f"<tr{destaque}><td style='padding:5px 10px;border-bottom:1px solid #e4e4e7'>{faixa_str}</td><td style='padding:5px 10px;border-bottom:1px solid #e4e4e7;text-align:right'>{valor_str}{badge}</td></tr>"
    return f"""<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:4px">
    <tr style="background:#18181b;color:#fff"><th style="padding:6px 10px;text-align:left">Faixa de valor</th><th style="padding:6px 10px;text-align:right">Custo</th></tr>
    {rows}
    </table>"""


def tabela_html(tabela, faixa_ativa_idx, titulo):
    """Mantido para compatibilidade — usa <details> HTML."""
    return f"""<details style="margin-top:8px">
    <summary style="cursor:pointer;font-size:13px;color:#3b82f6;font-weight:600">📋 Ver tabela completa — {titulo}</summary>
    {tabela_rows_html(tabela, faixa_ativa_idx)}
    </details>"""
