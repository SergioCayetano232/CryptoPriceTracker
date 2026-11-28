"""Tests de la página del panel."""

from datetime import datetime, timedelta, timezone

from crypto_tracker.config import Posicion, Watch
from crypto_tracker.informes import panel
from crypto_tracker.informes.panel_html import pagina
from crypto_tracker.puntuales import Puntual

AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _panel(**cambios):
    filas, _ = panel.filas_cartera(
        [Posicion("bitcoin", 0.1, 5000.0)], {"bitcoin": 60000.0}, {}, {}
    )
    datos = {
        "moneda": "eur",
        "filas": filas,
        "vigiladas": [],
        "alertas": [],
        "serie": [],
        "actualizado": AHORA - timedelta(minutes=2),
    }
    datos.update(cambios)
    return panel.Panel(**datos)


def test_sale_el_total_y_lo_ganado():
    html = pagina(_panel(), AHORA, parado=False)

    assert "€6.000,00" in html
    assert "€1.000,00</span> · +20,00 %" in html
    assert "Actualizado <time" in html
    assert ">hace 2 min</time>" in html


def test_el_total_sale_en_la_pestana():
    html = pagina(_panel(total_antes=5000.0), AHORA, parado=False)

    assert "<title>€6.000,00 · +20,00 %</title>" in html


def test_la_pestana_sin_24h_lleva_solo_el_total():
    html = pagina(_panel(), AHORA, parado=False)

    assert "<title>€6.000,00</title>" in html


def test_la_pestana_sin_cartera():
    html = pagina(_panel(filas=[]), AHORA, parado=False)

    assert "<title>Tu cartera · CryptoPriceTracker</title>" in html


def test_las_cifras_van_marcadas_para_poder_ocultarlas():
    html = pagina(_panel(), AHORA, parado=False)

    assert '<p class="total" data-k="total"><span class="dinero">€6.000,00' in html
    assert '<span class="dinero">0,1</span>' in html
    assert 'class="ojo"' in html
    # Los porcentajes no dicen cuánto tienes: se quedan a la vista.
    assert '<span class="dinero">+20' not in html


def test_el_icono_va_en_verde_si_sube_en_el_dia():
    html = pagina(_panel(total_antes=5000.0), AHORA, parado=False)

    assert '<link rel="icon" href="data:image/svg+xml,' in html
    assert "%230f9f6e" in html


def test_se_puede_instalar_como_app():
    from crypto_tracker.informes.panel_html import MANIFIESTO

    html = pagina(_panel(), AHORA, parado=False)

    assert '<link rel="manifest" href="manifest.webmanifest">' in html
    assert '<link rel="apple-touch-icon" href="icono-180.png">' in html
    assert MANIFIESTO["display"] == "standalone"
    assert [i["src"] for i in MANIFIESTO["icons"]] == ["icono-192.png", "icono-512.png"]


def test_la_app_instalada_abre_con_la_clave():
    from crypto_tracker.informes.panel_html import ANTES, manifiesto

    assert manifiesto("/manifest.webmanifest")["start_url"] == "./"
    assert manifiesto("/manifest.webmanifest?clave=a b&otro=1")["start_url"] == (
        "./?clave=a+b"
    )
    assert "'manifest.webmanifest' + location.search" in ANTES


def test_el_fondo_se_tine_con_el_miedo_del_mercado():
    from datetime import date

    from crypto_tracker.informes.panel_html import matiz
    from crypto_tracker.miedo import Indice

    html = pagina(_panel(miedo=Indice(20, "Fear", date(2026, 11, 28))), AHORA, False)

    assert '<body class="con-animo" style="--animo:28">' in html
    assert "Mercado: 😟 Miedo · 20/100" in html
    assert (matiz(0), matiz(50), matiz(100)) == (0, 70, 140)


def test_sin_miedo_el_fondo_de_siempre():
    html = pagina(_panel(), AHORA, parado=False)

    assert "<body>" in html
    assert 'class="animo"' not in html


def test_la_pagina_compartida_no_lleva_dinero():
    from crypto_tracker.informes.panel_html import pagina_compartida

    serie = [(AHORA - timedelta(days=1), 5800.0), (AHORA, 6000.0)]
    html = pagina_compartida(
        _panel(total_antes=5000.0, serie=serie), AHORA + timedelta(hours=24)
    )

    assert "€" not in html
    # Ni el total, ni lo ganado, ni el precio, ni la cantidad (el CSS aparte).
    cuerpo = html.split("<body", 1)[1]
    for cifra in ("6.000", "1.000", "60.000", 'class="dinero"'):
        assert cifra not in cuerpo
    assert ">+20,00 %</p>" in html  # desde la compra
    assert "+3,45 %" in html  # la semana
    assert "caduca el" in html
    assert '<meta name="robots" content="noindex">' in html
    assert "<script" not in html


def test_el_icono_va_en_rojo_si_baja_en_el_dia():
    assert "%23e0445a" in pagina(_panel(total_antes=7000.0), AHORA, parado=False)


def test_sin_dato_de_24h_el_icono_es_neutro():
    assert "%236d4aff" in pagina(_panel(), AHORA, parado=False)


def test_la_barra_del_movil_toma_el_fondo_de_cada_modo():
    html = pagina(_panel(), AHORA, parado=False)

    # Tienen que ser los --fondo del CSS, si no la barra no casa con la página.
    assert 'content="#f4f1fb" media="(prefers-color-scheme: light)"' in html
    assert 'content="#0d0b16" media="(prefers-color-scheme: dark)"' in html
    assert "--fondo: #f4f1fb;" in html
    assert "--fondo: #0d0b16;" in html


def test_al_pasar_el_raton_sale_la_hora_exacta():
    html = pagina(_panel(), AHORA, parado=False)

    local = (AHORA - timedelta(minutes=2)).astimezone()
    assert f'title="viernes {local:%d/%m} a las {local:%H:%M:%S}"' in html
    assert f'<span class="estado__hora"> · {local:%d/%m %H:%M}</span>' in html


def test_sin_precios_no_hay_hora_que_enseñar():
    html = pagina(_panel(actualizado=None), AHORA, parado=False)

    assert "todavía sin precios" in html
    assert "<time" not in html


def test_con_varias_criptos_hay_fila_de_total():
    filas, _ = panel.filas_cartera(
        [Posicion("bitcoin", 0.1, 5000.0), Posicion("ethereum", 1.0, 1500.0)],
        {"bitcoin": 60000.0, "ethereum": 2000.0},
        {},
        {},
    )

    html = pagina(_panel(filas=filas), AHORA, parado=False)

    assert 'class="fila fila--total"' in html
    assert '<small>invertido <span class="dinero">€6.500,00</span></small>' in html
    assert 'ganancia"><span class="dinero">€1.500,00</span><small>+23,08 %' in html


def test_con_una_sola_cripto_no_hay_total():
    assert 'class="fila fila--total"' not in pagina(_panel(), AHORA, parado=False)


def test_al_imprimir_quita_los_botones():
    html = pagina(_panel(), AHORA, parado=False)

    imprimir = html[html.index("@media print") :]
    assert (
        ".ojo, .copiar, .campana, .simulador, .repetir {\n    display: none;"
        in imprimir
    )


def test_el_estado_es_un_boton_para_actualizar():
    html = pagina(_panel(), AHORA, parado=False)

    assert '<button class="estado estado--vivo" type="button"' in html
    assert 'title="Actualizar ahora (R)"' in html
    assert 'title="Ocultar cifras (O)"' in html


def test_cada_cripto_enlaza_a_su_pagina_de_coingecko():
    html = pagina(_panel(), AHORA, parado=False)

    assert (
        '<a class="moneda" href="https://www.coingecko.com/es/monedas/bitcoin" '
        'target="_blank" rel="noopener">Bitcoin</a>'
    ) in html


def test_sin_historico_sale_una_raya_y_no_el_texto():
    html = pagina(_panel(), AHORA, parado=False)

    assert '<svg class="mini mini--vacia"' in html
    assert "<title>sin histórico</title>" in html
    assert ">sin histórico</span>" not in html


def test_el_titulo_de_la_grafica_lleva_lo_que_ha_cambiado():
    serie = [(AHORA - timedelta(hours=h), 6000.0 - h * 10) for h in range(10, 0, -1)]

    html = pagina(_panel(serie=serie), AHORA, parado=False)

    # De 5.900 a 5.990: un 1,53 % arriba.
    assert (
        'Los últimos 7 días · <span class="h2__cambio num--sube">+1,53 %</span>'
    ) in html


def test_con_el_bot_parado_el_icono_va_en_ambar():
    html = pagina(_panel(total_antes=5000.0), AHORA, parado=True)

    assert "%23d48a00" in html
    assert "%230f9f6e" not in html


def test_los_titulos_llevan_cuantas_hay():
    html = pagina(_panel(), AHORA, parado=False)

    assert '<h2>Lo que tienes <span class="h2__cuenta">1</span></h2>' in html
    # Sin ninguna, el título va solo: ya lo dice el texto de vacío.
    assert "<h2>Lo que vigilo</h2>" in html
    assert "<h2>Alertas pendientes</h2>" in html


def test_resalta_la_alerta_mas_cercana():
    lista = panel.alertas(
        [
            Puntual(1, "bitcoin", 70000.0, True),
            Puntual(2, "bitcoin", 50000.0, True),
            Puntual(3, "bitcoin", 63000.0, True),
        ],
        {"bitcoin": 60000.0},
        None,
    )

    html = pagina(_panel(alertas=lista), AHORA, parado=False)

    # La 2 ya ha llegado y tiene su "Ya está": la que más cerca está es la 3.
    assert html.count('class="fila fila--alerta fila--cerca"') == 1
    cerca = html.index("fila--alerta fila--cerca")
    assert html.index("#3 ·", cerca) < html.index("la más cerca", cerca)


def test_con_una_sola_alerta_no_resalta_nada():
    lista = panel.alertas(
        [Puntual(1, "bitcoin", 70000.0, True)], {"bitcoin": 1.0}, None
    )

    html = pagina(_panel(alertas=lista), AHORA, parado=False)

    assert 'class="fila fila--alerta fila--cerca"' not in html


def test_el_resumen_para_copiar():
    from crypto_tracker.informes.panel_html import resumen

    texto = resumen(_panel(total_antes=5000.0), AHORA, oculto=False)

    assert texto.splitlines() == [
        f"*Mi cartera* · {AHORA.astimezone():%d/%m}",
        "€6.000,00 · €1.000,00 (+20,00 % desde que compré)",
        "En 24 h: +20,00 %",
        "",
        "Bitcoin: €6.000,00 (100,0 %)",
    ]


def test_el_resumen_con_las_cifras_tapadas_no_lleva_dinero():
    from crypto_tracker.informes.panel_html import resumen

    texto = resumen(_panel(total_antes=5000.0), AHORA, oculto=True)

    assert "€" not in texto
    assert "+20,00 % desde que compré" in texto
    assert "Bitcoin: 100,0 % del total" in texto


def test_sin_cartera_no_hay_boton_de_copiar():
    assert 'class="copiar"' not in pagina(_panel(filas=[]), AHORA, parado=False)


def test_los_puntos_para_el_cursor_de_la_grafica():
    from crypto_tracker.informes.panel_html import puntos_cursor

    puntos = [(AHORA, 100.0), (AHORA + timedelta(hours=1), 200.0)]

    datos = puntos_cursor(puntos, "eur")

    local = AHORA.astimezone()
    # El más alto arriba del todo (0 %) y el más bajo abajo (100 %).
    assert datos[0] == [f"{local:%d/%m %H:%M}", "€100,00", 100.0, None]
    assert datos[1][1:] == ["€200,00", 0.0, None]


def test_grafica_plana_deja_el_cursor_a_media_altura():
    from crypto_tracker.informes.panel_html import puntos_cursor

    datos = puntos_cursor([(AHORA, 5.0), (AHORA, 5.0)], "eur")

    assert [d[2] for d in datos] == [50, 50]


def test_los_avisos_del_bot_van_en_la_pagina_para_el_navegador():
    from crypto_tracker.avisados import Aviso
    from crypto_tracker.informes.panel_html import avisos_navegador

    cuando = AHORA - timedelta(minutes=5)
    p = _panel(avisos={"bitcoin": Aviso(cuando, 63000.0, True)})

    avisos = avisos_navegador(p)

    hora = cuando.astimezone()
    assert avisos == [
        {
            "id": f"bitcoin@{cuando.isoformat()}",
            "titulo": "🔺 Bitcoin",
            "texto": f"Ha subido a €63.000,00 ({hora:%H:%M})",
        }
    ]
    assert "data-avisos=" in pagina(p, AHORA, parado=False)


def test_la_campana_sale_oculta_hasta_que_el_js_ve_que_hay_avisos():
    html = pagina(_panel(), AHORA, parado=False)

    assert '<button class="campana" type="button" aria-pressed="false" hidden>' in html


def test_el_simulador_lleva_lo_que_necesita_el_js():
    from crypto_tracker.informes.panel_html import datos_simulador

    datos = datos_simulador(_panel())

    assert datos["simbolo"] == "€"
    assert datos["monedas"] == [{"id": "bitcoin", "cantidad": 0.1, "precio": 60000.0}]
    assert datos["invertido"] == 5000.0
    # Los de impuestos.py, con el último tramo sin techo.
    assert datos["tramos"][0] == [6000, 19]
    assert datos["tramos"][-1] == [None, 30]


def test_el_simulador_no_cuenta_hacienda_en_otra_moneda():
    from crypto_tracker.informes.panel_html import datos_simulador

    html = pagina(_panel(moneda="usd"), AHORA, parado=False)

    assert datos_simulador(_panel(moneda="usd"))["tramos"] is None
    assert 'class="sim__hacienda' not in html


def test_sin_cartera_no_hay_simulador():
    html = pagina(_panel(filas=[]), AHORA, parado=False)

    assert "data-sim=" not in html


def test_la_grafica_dibuja_lo_mismo_en_bitcoin():
    filas, _ = panel.filas_cartera(
        [Posicion("ethereum", 1.0, 1500.0)], {"ethereum": 2000.0}, {}, {}
    )
    serie = [(AHORA - timedelta(hours=h), 2000.0) for h in range(10, 0, -1)]
    # Bitcoin sube un 9 % en esas horas (de 50.000 a 54.500) y la cartera no se mueve.
    btc = [
        (AHORA - timedelta(hours=h), 50000.0 + (10 - h) * 500) for h in range(11, 0, -1)
    ]

    html = pagina(_panel(filas=filas, serie=serie, serie_btc=btc), AHORA, parado=False)

    assert 'class="grafica__btc"' in html
    assert "€2.180,00</span>, <span" in html
    assert "€180,00</span> más de lo que tienes" in html


def test_si_solo_tienes_bitcoin_no_hay_segunda_linea():
    serie = [(AHORA - timedelta(hours=h), 6000.0 + h) for h in range(10, 0, -1)]
    btc = [(AHORA - timedelta(hours=h), 60000.0) for h in range(11, 0, -1)]

    html = pagina(_panel(serie=serie, serie_btc=btc), AHORA, parado=False)

    assert 'class="grafica__btc"' not in html


def test_nivel_de_cada_casilla():
    from crypto_tracker.informes.panel_html import nivel

    assert nivel(None) == "vacia"
    assert nivel(0.01) == "igual"
    assert nivel(0.5) == "sube-1"
    assert nivel(-2.0) == "baja-2"
    assert nivel(4.0) == "sube-3"
    assert nivel(-9.0) == "baja-4"


def test_el_calendario_en_la_pagina():
    hoy = AHORA.astimezone().date()
    lunes = hoy - timedelta(days=hoy.weekday())
    dias = [
        panel.Dia(lunes + timedelta(days=i), 100.0 + i, None if i == 0 else 1.0)
        for i in range(7)
        if lunes + timedelta(days=i) <= hoy
    ]
    dias += [
        panel.Dia(lunes + timedelta(days=i), None, None) for i in range(len(dias), 7)
    ]

    html = pagina(_panel(calendario=dias), AHORA, parado=False)

    assert "cal__dia--hoy" in html
    assert f"desde el\n  {lunes:%d/%m/%Y}" in html


def test_calendario_sin_dos_dias_seguidos_lo_explica():
    hoy = AHORA.astimezone().date()
    lunes = hoy - timedelta(days=hoy.weekday())
    dias = [panel.Dia(lunes + timedelta(days=i), None, None) for i in range(7)]
    dias[0] = panel.Dia(lunes, 100.0, None)

    html = pagina(_panel(calendario=dias), AHORA, parado=False)

    assert "Aún no hay dos días seguidos" in html


def test_sin_dias_no_hay_calendario():
    assert 'class="cal"' not in pagina(_panel(), AHORA, parado=False)


def test_sin_cartera_explica_como_ponerla():
    html = pagina(_panel(filas=[]), AHORA, parado=False)

    assert "Sin cartera" in html
    assert "/compra" in html
    assert "Lo que tienes" not in html


def test_avisa_si_el_bot_esta_parado():
    html = pagina(_panel(actualizado=AHORA - timedelta(hours=3)), AHORA, parado=True)

    assert "estado--parado" in html
    assert "no guarda precios desde <time" in html
    assert ">hace 3 h</time>" in html


def test_la_nota_de_una_alerta_no_se_cuela_como_html():
    [alerta] = panel.alertas(
        [Puntual(1, "bitcoin", 70000.0, True, nota="<script>x</script>")],
        {"bitcoin": 60000.0},
        None,
    )

    html = pagina(_panel(alertas=[alerta]), AHORA, parado=False)

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "16,7 %" in html
    assert "le falta subir" in html


def test_alerta_que_ya_ha_llegado():
    [alerta] = panel.alertas(
        [Puntual(1, "bitcoin", 50000.0, True)], {"bitcoin": 60000.0}, None
    )

    html = pagina(_panel(alertas=[alerta]), AHORA, parado=False)

    assert "Ya está" in html


def test_grafica_con_pocos_datos():
    html = pagina(_panel(), AHORA, parado=False)

    assert "Aún no hay precios suficientes" in html


def test_grafica_con_datos():
    serie = [(AHORA - timedelta(hours=h), 6000.0 + h) for h in range(10, 0, -1)]

    html = pagina(_panel(serie=serie), AHORA, parado=False)

    assert 'class="grafica__linea"' in html
    assert "€6.010,00" in html  # el máximo
    # El máximo es el primero de la serie y el mínimo el último.
    assert 'class="pico" style="left:0.0%' in html
    assert 'class="pico pico--abajo" style="left:100.0%' in html


def test_la_grafica_se_puede_repetir():
    serie = [(AHORA - timedelta(hours=h), 6000.0 + h) for h in range(10, 0, -1)]

    html = pagina(_panel(serie=serie), AHORA, parado=False)

    assert '<button class="repetir" type="button">▶ Ver cómo fue</button>' in html
    # Las líneas van dentro del recorte que el JS va abriendo al repetir.
    assert '<g clip-path="url(#corte)">' in html


def test_grafica_plana_marca_un_solo_punto():
    serie = [(AHORA - timedelta(hours=h), 6000.0) for h in range(5, 0, -1)]

    html = pagina(_panel(serie=serie), AHORA, parado=False)

    assert "grafica__picos--plana" in html
    assert html.count('class="pico__cifra"') == 1


def test_vigiladas_con_su_regla():
    v = panel.Vigilada("bitcoin", Watch("bitcoin", percent=5), 60000.0, 2.5)

    html = pagina(_panel(vigiladas=[v]), AHORA, parado=False)

    assert "cada 5 % que se mueva" in html
    assert "+2,50 %" in html


def test_siempre_lleva_lo_de_coingecko():
    # El plan gratis pide citarles junto a los datos.
    assert "Price data by CoinGecko" in pagina(_panel(), AHORA, parado=False)


def test_la_version_es_la_del_pyproject():
    # Antes salía la de __init__.py, que se quedó en 0.1.0.
    from crypto_tracker import version

    assert f"CryptoPriceTracker {version.numero()} ·" in pagina(
        _panel(), AHORA, parado=False
    )


def test_en_el_movil_la_ganancia_va_a_la_derecha_aunque_no_haya_mini():
    # Sin histórico la mini es un <span>: contando spans, la regla del móvil
    # movía el valor en vez de la ganancia.
    html = pagina(_panel(), AHORA, parado=False)

    assert "sin histórico" in html
    assert 'class="num num--sube ganancia"><span class="dinero">€1.000,00' in html
    assert ".lista--cartera .fila > .ganancia { grid-column: 2; }" in html
    assert "nth-of-type" not in html
