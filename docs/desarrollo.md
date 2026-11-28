# Para desarrolladores

[← Volver al README](../README.md)

El código está en `crypto_tracker/`, repartido en carpetas por tema. Cada
comando tiene su módulo con las cuentas, sin nada de Telegram; lo que contesta
el bot va en `respuestas/` y los textos, en `mensajes/`. `main.py` lo une todo.

Dentro del paquete los imports son relativos (`from ..nucleo import database`);
en los tests y en `main.py`, absolutos (`from crypto_tracker.nucleo import
database`). Si añades una carpeta, lleva su `__init__.py`.

```
crypto_tracker/
  version.py            la versión, para /version; aquí para encontrar pyproject.toml

  nucleo/               lo que lo mueve todo: configuración, base de datos, Telegram y precios
    ajustes.py          lo que tienes puesto en el .env, para /ajustes
    backup.py           el zip con la base de datos, para /backup
    binance.py          precios de respaldo por si CoinGecko no contesta
    botones.py          los botones de debajo de los avisos
    coingecko.py        consulta los precios
    comandos.py         entiende lo que le escribes
    config.py           lee el .env
    copia.py            lo de ahora escrito como va en el .env, para /copia
    cuota.py            cuenta las consultas a CoinGecko
    database.py         guarda el histórico
    inline.py           modo inline: escribes @tubot btc en cualquier chat y mandas el precio
    latido.py           el toque a un servicio de fuera, por si se cae el servidor
    lenguaje.py         frases sin barra, como "avísame si btc baja de 60000"
    moneda.py           la moneda que pides al final de /precio
    periodo.py          lee tramos como 7d
    rellenar.py         qué precios pasados faltan, para /rellenar
    salud.py            avisa si el bot deja de funcionar
    simbolos.py         btc, eth... a su id de CoinGecko
    telegram.py         manda los mensajes
    temas.py            los temas en que se reparte /ayuda
    usuarios.py         los invitados de /invitar, cada uno con su archivo
    vigiladas.py        lo que cambias con /vigilar

  avisos/               los avisos y alertas, y lo que te recuerda el bot por su cuenta
    alertaratio.py      /alerta eth/btc 0.05: avisa una vez cuando una valga eso en la otra
    alerts.py           decide cuándo avisar y escribe los avisos
    avisados.py         el último aviso de cada una, para /ultimo
    aviso_tendencias.py cuándo avisar de que algo tuyo está de moda
    avisorsi.py         cuándo avisar de sobrecompra o sobreventa
    bajon.py            aviso de cuando la cartera cae mucho desde su récord, sin tener que preguntar
    brusco.py           los movimientos bruscos
    buzon.py            junta los avisos del mismo ciclo en un mensaje
    cada.py             /cada: un comando que te mando yo solo, cada día o un día de la semana
    callar.py           entiende /mute con una sola cripto
    calma.py            cuándo una se queda muy quieta, para /tormenta y AVISO_CALMA
    concentracion.py    aviso de cuando una sola cripto se come casi toda la cartera
    condicion.py        lo del miedo o el RSI que puede llevar una /alerta
    contexto.py         qué pasó otras veces que se movió así, para los avisos
    cruce.py            la cruz dorada y la de la muerte
    diario.py           el resumen diario y las horas tranquilas
    direccion.py        vigila direcciones de bitcoin (mempool.space) y ethereum, para /direccion
    envivo.py           el mensaje fijado que se edita solo, para /envivo
    escalera.py         vender por tramos al subir o comprar al bajar, para /escalera
    estables.py         cuándo una estable se sale de su dólar
    extremos.py         los máximos y mínimos de los últimos días
    juntas.py           avisa cuando dos que iban a la vez se separan, para /juntas
    perdido.py          lo que ha pasado mientras el bot estaba callado, para contártelo al volver
    proximo.py          a qué precio salta el siguiente aviso
    puntuales.py        las alertas de /alerta
    recordar.py         /recordar: un aviso cada semana de tu compra periódica, con botón para apuntarla
    rezagada.py         /rezagada: avisa cuando una lleva una semana haciéndolo mucho peor que otra
    ruido.py            los avisos que se dieron la vuelta, para /ruido
    salvo.py            lo de /mute ... salvo 10%
    stop.py             /stop: avisa al perder o ganar un % sobre lo que te costó, no sobre lo de ahora
    volumen.py          cuándo se negocia mucho más de lo normal, para AVISO_VOLUMEN
    voto.py             los 👍 y 👎 de los avisos, que luego mira /ruido

  inversion/            tu cartera: compras, ventas y cómo te va con lo que tienes
    apy.py              cuánta cripto tendrías en staking, para /apy
    arrepentido.py      lo que valdría hoy lo vendido, para /arrepentido
    cartera.py          cuánto vale lo que tienes
    comision.py         la comisión de /compra o /venta: 'com 1.5' en dinero o 'com 0.1%' de lo movido
    comisiones.py       lo pagado en comisiones, para /comisiones
    compras.py          /compras: tu mejor y tu peor compra, y cuántas van ganando
    convertir.py        entiende lo que le pides a /convertir
    corregir.py         rehacer los movimientos al cambiar uno, para /corregir
    cuenta_binance.py   tus saldos de Binance con una clave de lectura, para /binance
    dca.py              las compras periódicas de /dca
    deposito.py         tu cartera contra un depósito, para /deposito
    doble.py            a qué precio doblas lo que metiste, para /doble
    emocion.py          con qué ánimo compras y vendes, para /emociones
    equilibrio.py       a qué precio dejas de perder, para /equilibrio
    fantasma.py         la cartera de mentira de /fantasma
    futuro.py           entre qué cifras puede estar tu cartera, para /futuro
    ganancias.py        lo ganado con lo vendido, para /ganancias
    herencia.py         lo que tienes y dónde, para /herencia, sin claves
    hodl.py             los días que llevas sin vender, para /hodl
    hubiera.py          entiende lo que le pides a /si
    ideal.py            el reparto que quieres y cuándo avisar de que te alejas, para /ideal
    importar.py         lee el CSV de Binance o de Kraken, para /importar
    inflacion.py        tu cartera contra el IPC de España, para /inflacion
    limite.py           lo que llevas comprado este mes, para /limite
    meta.py             cuánto le falta a tu cartera para una cifra, para /meta
    mitad.py            a qué precio pierdes la mitad, para /mitad
    movimientos.py      las compras y ventas de /compra y /venta
    nota.py             el porqué de una /compra o /venta: lo que va detrás de los números
    objetivo.py         lo que valdría tu cartera, para /objetivo
    pelotazo.py         tu mejor y tu peor compra, para /pelotazo
    pienso.py           las compras que te estás pensando, para /pienso
    plan.py             cuánto tardas en llegar a una cifra, para /plan
    posicion.py         cuánto meter según lo que aceptas perder, para /posicion
    primera.py          tu primera compra, para /primera
    promediar.py        cuánto comprar para bajar tu precio medio, para /promediar
    rebalanceo.py       /rebalanceo: qué comprar y qué vender para dejar la cartera como digas
    record.py           lo máximo que ha valido tu cartera, para /record
    rentabilidad.py     /rentabilidad: lo que ganas al año, contando cuándo metiste y sacaste cada euro
    reparto.py          qué parte de la cartera es cada una, para /reparto
    riesgo.py           /riesgo: cuánto depende tu cartera de una sola cripto y cuánto se mueve
    sesgo.py            el índice de miedo de tus compras y ventas, para /sesgo
    sharpe.py           lo que gana la cartera para lo que se mueve, para /sharpe
    tesis.py            por qué compraste y si acertaste, para /tesis
    timing.py           /timing: si aciertas el momento o daría igual comprar un día cualquiera
    vsbolsa.py          tu cartera contra un indexado, con Yahoo, para /vsbolsa
    vsbtc.py            /vsbtc: tu cartera contra haber metido lo mismo en bitcoin, en las mismas fechas

  hacienda/             lo que toca a Hacienda: ventas con FIFO, la Renta y el informe fiscal
    aviso_renta.py      cuándo avisar en abril de que toca la Renta
    compensar.py        qué vender en pérdidas, para /compensar
    fifo.py             qué costó lo vendido, contando primero lo más viejo
    impuestos.py        los tramos del IRPF, para /impuestos
    informe.py          las cuentas del año juntas, para /informe
    informe_pdf.py      dibuja el PDF de /informe
    modelo721.py        si te toca declarar las criptos de fuera, para /modelo721
    permuta.py          lo que pagas a Hacienda al cambiar una cripto por otra, para /permuta
    renta.py            cada venta con FIFO en un CSV, para /impuestos csv
    sivendo.py          lo que ganarías y pagarías antes de vender, para /sivendo

  indicadores/          precios, mercado e indicadores para analizar cada cripto
    ahr999.py           el índice de comprar fuerte, DCA o esperar, para /ahr999
    altseason.py        cuántas grandes le ganan a bitcoin, para /altseason
    arcoiris.py         la curva de bitcoin y sus nueve franjas, para /arcoiris
    backtest.py         vender al subir y recomprar al bajar, para /backtest
    bollinger.py        las bandas de 20 días, para /bollinger
    caida.py            lo que ha bajado desde el máximo, para /caida
    calendario.py       /calendario: el mes de una cripto, cada día en verde o en rojo
    ciclo.py            el voto de cada indicador de ciclo, para /ciclo
    cme.py              el hueco del fin de semana en los futuros del CME, para /cme
    comisionred.py      lo que cuesta mover bitcoin, de mempool.space, para /comisionred
    comparar.py         el ranking de /comparar
    correlacion.py      si dos criptos se mueven juntas, para /correlacion
    cuando.py           la última vez que estuvo a un precio, para /cuando
    dia.py              a cuánto estaba un día concreto, para /dia
    diames.py           qué día del mes sale más barato, para /diames
    diasemana.py        lo que cambia cada día de la semana, para /diasemana
    dificultad.py       el próximo ajuste y la potencia de minado, para /dificultad
    dominancia.py       cómo cambia la parte de bitcoin, para /dominancia
    dvol.py             lo que las opciones de Deribit esperan que se mueva, para /dvol
    estacional.py       qué meses suele subir, con las velas de Binance, para /estacional
    estocastico.py      dónde está dentro del rango de 14 días, para /estocastico
    fibonacci.py        los niveles entre el máximo y el mínimo, para /fibonacci
    funding.py          lo que se pagan los de futuros en Binance, para /funding
    gwei.py             lo que cuesta ahora hacer algo en Ethereum, para /gwei
    halving.py          cuánto falta para el próximo halving, para /halving
    hashribbons.py      las medias de 30 y 60 días del hashrate, para /hashribbons
    horas.py            la hora más barata y la más cara, para /horas
    hoy.py              cómo van desde las 00:00, para /hoy
    kimchi.py           lo que se paga de más en Corea, para /kimchi
    lightning.py        cuánto bitcoin hay en Lightning, de 1ml.com, para /lightning
    longshort.py        cuántos apuestan a cada lado en Binance, para /longshort
    macd.py             las medias de 12 y 26 días contra la de 9, para /macd
    mapa.py             las grandes en recuadros por tamaño, para /mapa
    maximo.py           el máximo histórico de /ath
    maxpain.py          las opciones del viernes y su max pain, para /maxpain
    mayer.py            el precio entre su media de 200 días, para /mayer
    media.py            las medias de 7, 30 y 90 días, para /media
    mejor.py            el mejor y el peor día, para /extremo
    mercado.py          el mercado entero, para /mercado
    miedo.py            /miedo: el indice de miedo y codicia del mercado cripto, de alternative.me
    millonario.py       lo que hace falta para un millón, para /millonario
    mvrv.py             el precio frente al realizado y su Z-score, para /mvrv
    oi.py               lo apostado en futuros de Binance, para /oi
    paciencia.py        cuántas veces salía bien comprar y aguantar, para /paciencia
    picycle.py          la media de 111 días contra el doble de la de 350, para /picycle
    precio.py           /precio: lo que vale una cripto y como va en 1 h, en 24 h y en una semana
    premium.py          lo que se paga de más en Coinbase, para /premium
    profundidad.py      lo que cuesta mover el precio en Binance, para /profundidad
    quieta.py           la que menos se mueve, para /quieta
    racha.py            los días seguidos subiendo o bajando, para /racha
    rango.py            el máximo, el mínimo y la media de /rango
    ratio.py            lo que vale una cripto en otra, para /ratio
    redondo.py          la siguiente cifra redonda, para /redondo
    rsi.py              el RSI de 14 días, para /rsi
    sat.py              lo que vale un satoshi, para /sat
    sectores.py         qué tipo de cripto sube hoy, para /sectores
    semaforo.py         el voto de cada indicador y la luz que sale, para /semaforo
    soporte.py          dónde ha girado varias veces, para /soporte
    spread.py           CoinGecko contra Binance, para /spread
    sube.py             lo que ha subido desde el mínimo, para /sube
    suelo.py            bitcoin frente a su media de 200 semanas, para /suelo
    tendencias.py       lo que más se busca, para /tendencias
    top.py              /top: las que mas suben y las que mas bajan hoy entre las mas grandes
    velas.py            el precio agrupado en velas, para /historico ... velas
    verdes.py           los días que sube y los que baja, para /verdes
    volatilidad.py      lo que se mueve cada día, para /volatilidad

  informes/             el panel web, las gráficas, las tarjetas y los resúmenes periódicos
    aniversario.py      las compras que cumplen años, para el resumen del día
    anual.py            tu año en cripto: llega el 1 de enero, y con /anual 2026 cuando quieras
    exportar.py         los CSV de /exportar, de precios y de movimientos
    grafica.py          las imágenes de /historico y /cartera
    icono_app.py        el icono del panel instalado como app en el móvil
    mensual.py          el resumen del mes que acaba de terminar, que llega el día 1
    mes.py              desde cuándo cuentan el mes y el año, para /mes y /anual
    panel.py            los datos del panel web de --panel
    panel_html.py       la página del panel
    resumenia.py        /resumenia: tu semana contada en cuatro frases por Claude, con tus datos
    semanal.py          el resumen de la semana de la cartera
    tarjeta.py          tu cartera en %, para la imagen de /tarjeta
    tarjeta_anual.py    tu año en %, para la imagen de /anual 2025 tarjeta

  equivalencias/        los «cuántos X te da tu cartera»: cafés, jamones, pisos
    enletras.py         tu cartera escrita en letras, para /enletras
    equivale.py         /equivale: los «cuántos X te da tu cartera» en un solo comando
    mundo.py            los bitcoin repartidos entre todos, para /mundo
    navidad.py          los días que faltan para Navidad, para /navidad
    nochevieja.py       lo que queda de año, para /nochevieja
    pizza.py            los 10.000 BTC de las pizzas, para /pizza
    (los demás)         un archivo por cosa: aceite, airpods, alquiler, ave, bici,
                        bigmac, boda, cafe, cana, carnet, churros, cine, coche,
                        concierto, croquetas, futbol, gasolina, gimnasio, hotel,
                        iphone, jamon, kebab, lambo, libro, loteria, luz, macbook,
                        menu, metro, netflix, oro, paella, pan, peluqueria, piso,
                        ps5, rolex, sofa, spotify, sueldo, supermercado, switch,
                        taxi, tesla, tortilla, videojuego, vuelo, zapatillas

  curiosidades/         juegos, bromas y fechas del mundo cripto, para pasar el rato
    adios.py            el tiempo sin Satoshi, para /adios
    adivina.py          cuánto te has acercado al precio, para /adivina
    aleatoria.py        una de las más grandes al azar, para /aleatoria
    apodo.py            un mote según cómo llevas la cartera, para /apodo
    ballena.py          qué bicho eres según tus bitcoin, para /ballena
    bola.py             las respuestas de /bola
    caraocruz.py        la moneda al aire de /caraocruz
    chiste.py           los chistes de /chiste
    consejo.py          los consejos malos de /consejo
    cumple.py           los años de Bitcoin, para /cumple
    dado.py             el dado de /dado
    dato.py             los datos curiosos de /dato
    emoji.py            la cara de tu cartera hoy, para /emoji
    encuesta.py         la encuesta de cada lunes, que se apunta como /prediccion
    ethereum.py         los años de Ethereum, para /ethereum
    excusa.py           las excusas de /excusa
    frase.py            las frases famosas de /frase
    galleta.py          las frases de /galleta
    glosario.py         las palabras que explica /glosario
    horoscopo.py        los signos y predicciones de /horoscopo
    liga.py             la clasificación de /prediccion entre todos, para /liga
    merge.py            los años de The Merge de Ethereum, para /merge
    ppt.py              piedra, papel o tijera, para /ppt
    prediccion.py       a cuánto estará el domingo y tu marcador, para /prediccion
    quiz.py             las preguntas de /quiz
    refran.py           los refranes de /refran
    tarot.py            las cartas de /tarot
    tiempo.py           tu cartera como el parte del tiempo, para /tiempo
    whitepaper.py       los años del whitepaper, para /whitepaper

  mensajes/             los textos que manda el bot, partidos por temas
  respuestas/           lo que contesta a cada comando, por temas
    base.py             lo que comparten todos
    mercado.py          /precio, /top, /miedo, /dominancia...
    analisis.py         /rsi, /macd, /soporte, /racha...
    cartera.py          /compra, /venta, /impuestos, /rentabilidad...
    alertas.py          /alerta, /vigilar, /stop, /escalera...
    resumenes.py        el resumen del día, la semana, el mes y el año
    recordatorios.py    /recordar, /pienso y /prediccion
    revisiones.py       los avisos del ciclo aparte de los de precio
    comparaciones.py    /equivale y los «cuántos X te da tu cartera»
    datos.py            /exportar, /backup y /rellenar
    ratos.py            /horoscopo, /bola, /quiz...

main.py                 el ciclo, el bucle de Telegram y la lista de comandos
tests/                  los tests, en las mismas carpetas que el código; en la raíz,
                        los de main.py, la versión y el empaquetado
windows/                para dejarlo corriendo en un servidor Windows
linux/                  lo mismo en un servidor Linux, con systemd
Dockerfile              la imagen, y docker-compose.yml para arrancarla
```

Pasar los tests y el linter (instala las versiones fijadas en `pyproject.toml`):
```
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

En GitHub se pasan solos en cada push, con Python 3.10 y 3.14.
