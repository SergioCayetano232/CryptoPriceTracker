# Para desarrolladores

[← Volver al README](../README.md)

```
crypto_tracker/
  config.py      lee el .env
  coingecko.py   consulta los precios
  binance.py     precios de respaldo por si CoinGecko no contesta
  comisionred.py lo que cuesta mover bitcoin, de mempool.space, para /comisionred
  dificultad.py  el próximo ajuste y la potencia de minado, para /dificultad
  hashribbons.py las medias de 30 y 60 días del hashrate, para /hashribbons
  gwei.py        lo que cuesta ahora hacer algo en Ethereum, para /gwei
  lightning.py   cuánto bitcoin hay en Lightning, de 1ml.com, para /lightning
  spread.py      CoinGecko contra Binance, para /spread
  funding.py     lo que se pagan los de futuros en Binance, para /funding
  oi.py          lo apostado en futuros de Binance, para /oi
  longshort.py   cuántos apuestan a cada lado en Binance, para /longshort
  profundidad.py lo que cuesta mover el precio en Binance, para /profundidad
  premium.py     lo que se paga de más en Coinbase, para /premium
  kimchi.py      lo que se paga de más en Corea, para /kimchi
  direccion.py   vigila direcciones de bitcoin (mempool.space) y ethereum, para /direccion
  database.py    guarda el histórico
  usuarios.py    los invitados de /invitar, cada uno con su archivo
  telegram.py    manda los mensajes
  botones.py     los botones de debajo de los avisos
  voto.py        los 👍 y 👎 de los avisos, que luego mira /ruido
  envivo.py      el mensaje fijado que se edita solo, para /envivo
  ideal.py       el reparto que quieres y cuándo avisar de que te alejas, para /ideal
  buzon.py       junta los avisos del mismo ciclo en un mensaje
  alerts.py      decide cuándo avisar y escribe los avisos
  brusco.py      los movimientos bruscos
  extremos.py    los máximos y mínimos de los últimos días
  comparar.py    el ranking de /comparar
  quieta.py      la que menos se mueve, para /quieta
  correlacion.py si dos criptos se mueven juntas, para /correlacion
  juntas.py      avisa cuando dos que iban a la vez se separan, para /juntas
  ratio.py       lo que vale una cripto en otra, para /ratio
  convertir.py   entiende lo que le pides a /convertir
  exportar.py    los CSV de /exportar, de precios y de movimientos
  importar.py    lee el CSV de Binance o de Kraken, para /importar
  cuenta_binance.py  tus saldos de Binance con una clave de lectura, para /binance
  rellenar.py    qué precios pasados faltan, para /rellenar
  hubiera.py     entiende lo que le pides a /si
  objetivo.py    lo que valdría tu cartera, para /objetivo
  limite.py      lo que llevas comprado este mes, para /limite
  apy.py         cuánta cripto tendrías en staking, para /apy
  deposito.py    tu cartera contra un depósito, para /deposito
  inflacion.py   tu cartera contra el IPC de España, para /inflacion
  vsbolsa.py     tu cartera contra un indexado, con Yahoo, para /vsbolsa
  comisiones.py  lo pagado en comisiones, para /comisiones
  plan.py        cuánto tardas en llegar a una cifra, para /plan
  posicion.py    cuánto meter según lo que aceptas perder, para /posicion
  promediar.py   cuánto comprar para bajar tu precio medio, para /promediar
  meta.py        cuánto le falta a tu cartera para una cifra, para /meta
  equilibrio.py  a qué precio dejas de perder, para /equilibrio
  doble.py       a qué precio doblas lo que metiste, para /doble
  mitad.py       a qué precio pierdes la mitad, para /mitad
  salvo.py       lo de /mute ... salvo 10%
  callar.py      entiende /mute con una sola cripto
  dca.py         las compras periódicas de /dca
  maximo.py      el máximo histórico de /ath
  tendencias.py  lo que más se busca, para /tendencias
  aviso_tendencias.py  cuándo avisar de que algo tuyo está de moda
  aleatoria.py   una de las más grandes al azar, para /aleatoria
  caraocruz.py   la moneda al aire de /caraocruz
  ppt.py         piedra, papel o tijera, para /ppt
  adivina.py     cuánto te has acercado al precio, para /adivina
  dado.py        el dado de /dado
  frase.py       las frases famosas de /frase
  consejo.py     los consejos malos de /consejo
  excusa.py      las excusas de /excusa
  refran.py      los refranes de /refran
  horoscopo.py   los signos y predicciones de /horoscopo
  bola.py        las respuestas de /bola
  galleta.py     las frases de /galleta
  tarot.py       las cartas de /tarot
  chiste.py      los chistes de /chiste
  dato.py        los datos curiosos de /dato
  quiz.py        las preguntas de /quiz
  glosario.py    las palabras que explica /glosario
  mercado.py     el mercado entero, para /mercado
  dominancia.py  cómo cambia la parte de bitcoin, para /dominancia
  altseason.py   cuántas grandes le ganan a bitcoin, para /altseason
  mapa.py        las grandes en recuadros por tamaño, para /mapa
  sectores.py    qué tipo de cripto sube hoy, para /sectores
  halving.py     cuánto falta para el próximo halving, para /halving
  cumple.py      los años de Bitcoin, para /cumple
  whitepaper.py  los años del whitepaper, para /whitepaper
  merge.py       los años de The Merge de Ethereum, para /merge
  ethereum.py    los años de Ethereum, para /ethereum
  adios.py       el tiempo sin Satoshi, para /adios
  pizza.py       los 10.000 BTC de las pizzas, para /pizza
  mundo.py       los bitcoin repartidos entre todos, para /mundo
  millonario.py  lo que hace falta para un millón, para /millonario
  lambo.py       tu cartera en Lamborghinis, para /lambo
  enletras.py    tu cartera escrita en letras, para /enletras
  ballena.py     qué bicho eres según tus bitcoin, para /ballena
  cafe.py        tu cartera en cafés, para /cafe
  sueldo.py      tu cartera en salarios mínimos, para /sueldo
  gasolina.py    tu cartera en litros de gasolina, para /gasolina
  bigmac.py      tu cartera en Big Macs, para /bigmac
  iphone.py      tu cartera en iPhones, para /iphone
  alquiler.py    tu cartera en meses de alquiler, para /alquiler
  oro.py         tu cartera en gramos de oro, para /oro
  netflix.py     tu cartera en meses de Netflix, para /netflix
  ps5.py         tu cartera en PS5, para /ps5
  tesla.py       tu cartera en Teslas, para /tesla
  spotify.py     tu cartera en meses de Spotify, para /spotify
  cana.py        tu cartera en cañas, para /cana
  switch.py      tu cartera en Switch 2, para /switch
  cine.py        tu cartera en entradas de cine, para /cine
  gimnasio.py    tu cartera en meses de gimnasio, para /gimnasio
  vuelo.py       tu cartera en vuelos a Nueva York, para /vuelo
  supermercado.py tu cartera en carros de la compra, para /super
  kebab.py       tu cartera en kebabs, para /kebab
  metro.py       tu cartera en meses de abono de transporte, para /metro
  luz.py         tu cartera en facturas de la luz, para /luz
  libro.py       tu cartera en libros, para /libro
  concierto.py   tu cartera en entradas de concierto, para /concierto
  airpods.py     tu cartera en AirPods Pro, para /airpods
  zapatillas.py  tu cartera en pares de zapatillas, para /zapatillas
  ave.py         tu cartera en viajes en AVE a Barcelona, para /ave
  menu.py        tu cartera en menús del día, para /menu
  hotel.py       tu cartera en noches de hotel, para /hotel
  peluqueria.py  tu cartera en cortes de pelo, para /peluqueria
  macbook.py     tu cartera en MacBooks, para /macbook
  bici.py        tu cartera en bicis de carretera, para /bici
  churros.py     tu cartera en chocolate con churros, para /churros
  loteria.py     tu cartera en décimos de Navidad, para /loteria
  piso.py        tu cartera en metros de piso en Madrid, para /piso
  futbol.py      tu cartera en entradas de fútbol, para /futbol
  taxi.py        tu cartera en taxis al aeropuerto, para /taxi
  tortilla.py    tu cartera en pinchos de tortilla, para /tortilla
  videojuego.py  tu cartera en videojuegos, para /videojuego
  sofa.py        tu cartera en sofás, para /sofa
  coche.py       tu cartera en coches, para /coche
  boda.py        tu cartera en bodas, para /boda
  jamon.py       tu cartera en jamones, para /jamon
  rolex.py       tu cartera en Rolex, para /rolex
  aceite.py      tu cartera en aceite de oliva, para /aceite
  paella.py      tu cartera en paellas, para /paella
  croquetas.py   tu cartera en croquetas, para /croquetas
  pan.py         tu cartera en barras de pan, para /pan
  emoji.py       la cara de tu cartera hoy, para /emoji
  tiempo.py      tu cartera como el parte del tiempo, para /tiempo
  carnet.py      tu cartera en carnets de conducir, para /carnet
  navidad.py     los días que faltan para Navidad, para /navidad
  nochevieja.py  lo que queda de año, para /nochevieja
  sat.py         lo que vale un satoshi, para /sat
  puntuales.py   las alertas de /alerta
  pienso.py      las compras que te estás pensando, para /pienso
  tesis.py       por qué compraste y si acertaste, para /tesis
  fantasma.py    la cartera de mentira de /fantasma
  herencia.py    lo que tienes y dónde, para /herencia, sin claves
  escalera.py    vender por tramos al subir o comprar al bajar, para /escalera
  emocion.py     con qué ánimo compras y vendes, para /emociones
  prediccion.py  a cuánto estará el domingo y tu marcador, para /prediccion
  liga.py        la clasificación de /prediccion entre todos, para /liga
  encuesta.py    la encuesta de cada lunes, que se apunta como /prediccion
  condicion.py   lo del miedo o el RSI que puede llevar una /alerta
  vigiladas.py   lo que cambias con /vigilar
  volatilidad.py lo que se mueve cada día, para /volatilidad
  contexto.py    qué pasó otras veces que se movió así, para los avisos
  ruido.py       los avisos que se dieron la vuelta, para /ruido
  movimientos.py las compras y ventas de /compra y /venta
  ganancias.py   lo ganado con lo vendido, para /ganancias
  arrepentido.py lo que valdría hoy lo vendido, para /arrepentido
  corregir.py    rehacer los movimientos al cambiar uno, para /corregir
  impuestos.py   los tramos del IRPF, para /impuestos
  renta.py       cada venta con FIFO en un CSV, para /impuestos csv
  informe.py     las cuentas del año juntas, para /informe
  informe_pdf.py dibuja el PDF de /informe
  fifo.py        qué costó lo vendido, contando primero lo más viejo
  permuta.py     lo que pagas a Hacienda al cambiar una cripto por otra, para /permuta
  sivendo.py     lo que ganarías y pagarías antes de vender, para /sivendo
  compensar.py   qué vender en pérdidas, para /compensar
  aviso_renta.py cuándo avisar en abril de que toca la Renta
  modelo721.py   si te toca declarar las criptos de fuera, para /modelo721
  primera.py     tu primera compra, para /primera
  pelotazo.py    tu mejor y tu peor compra, para /pelotazo
  apodo.py       un mote según cómo llevas la cartera, para /apodo
  hodl.py        los días que llevas sin vender, para /hodl
  record.py      lo máximo que ha valido tu cartera, para /record
  proximo.py     a qué precio salta el siguiente aviso
  cartera.py     cuánto vale lo que tienes
  grafica.py     las imágenes de /historico y /cartera
  panel.py       los datos del panel web de --panel
  panel_html.py  la página del panel
  media.py       las medias de 7, 30 y 90 días, para /media
  racha.py       los días seguidos subiendo o bajando, para /racha
  verdes.py      los días que sube y los que baja, para /verdes
  mejor.py       el mejor y el peor día, para /extremo
  diasemana.py   lo que cambia cada día de la semana, para /diasemana
  diames.py      qué día del mes sale más barato, para /diames
  estacional.py  qué meses suele subir, con las velas de Binance, para /estacional
  mayer.py       el precio entre su media de 200 días, para /mayer
  arcoiris.py    la curva de bitcoin y sus nueve franjas, para /arcoiris
  suelo.py       bitcoin frente a su media de 200 semanas, para /suelo
  mvrv.py        el precio frente al realizado y su Z-score, para /mvrv
  ciclo.py       el voto de cada indicador de ciclo, para /ciclo
  picycle.py     la media de 111 días contra el doble de la de 350, para /picycle
  ahr999.py      el índice de comprar fuerte, DCA o esperar, para /ahr999
  paciencia.py   cuántas veces salía bien comprar y aguantar, para /paciencia
  cme.py         el hueco del fin de semana en los futuros del CME, para /cme
  dvol.py        lo que las opciones de Deribit esperan que se mueva, para /dvol
  maxpain.py     las opciones del viernes y su max pain, para /maxpain
  horas.py       la hora más barata y la más cara, para /horas
  reparto.py     qué parte de la cartera es cada una, para /reparto
  tarjeta.py     tu cartera en %, para la imagen de /tarjeta
  tarjeta_anual.py  tu año en %, para la imagen de /anual 2025 tarjeta
  rango.py       el máximo, el mínimo y la media de /rango
  soporte.py     dónde ha girado varias veces, para /soporte
  dia.py         a cuánto estaba un día concreto, para /dia
  cuando.py      la última vez que estuvo a un precio, para /cuando
  avisados.py    el último aviso de cada una, para /ultimo
  avisorsi.py    cuándo avisar de sobrecompra o sobreventa
  estables.py    cuándo una estable se sale de su dólar
  cruce.py       la cruz dorada y la de la muerte
  volumen.py     cuándo se negocia mucho más de lo normal, para AVISO_VOLUMEN
  calma.py       cuándo una se queda muy quieta, para /tormenta y AVISO_CALMA
  redondo.py     la siguiente cifra redonda, para /redondo
  rsi.py         el RSI de 14 días, para /rsi
  semaforo.py    el voto de cada indicador y la luz que sale, para /semaforo
  bollinger.py   las bandas de 20 días, para /bollinger
  macd.py        las medias de 12 y 26 días contra la de 9, para /macd
  estocastico.py dónde está dentro del rango de 14 días, para /estocastico
  velas.py       el precio agrupado en velas, para /historico ... velas
  fibonacci.py   los niveles entre el máximo y el mínimo, para /fibonacci
  futuro.py      entre qué cifras puede estar tu cartera, para /futuro
  sharpe.py      lo que gana la cartera para lo que se mueve, para /sharpe
  sesgo.py       el índice de miedo de tus compras y ventas, para /sesgo
  caida.py       lo que ha bajado desde el máximo, para /caida
  backtest.py    vender al subir y recomprar al bajar, para /backtest
  sube.py        lo que ha subido desde el mínimo, para /sube
  periodo.py     lee tramos como 7d
  moneda.py      la moneda que pides al final de /precio
  simbolos.py    btc, eth... a su id de CoinGecko
  diario.py      el resumen diario y las horas tranquilas
  hoy.py         cómo van desde las 00:00, para /hoy
  semanal.py     el resumen de la semana de la cartera
  mes.py         desde cuándo cuentan el mes y el año, para /mes y /anual
  salud.py       avisa si el bot deja de funcionar
  latido.py      el toque a un servicio de fuera, por si se cae el servidor
  version.py     la versión del bot, para /version
  copia.py       lo de ahora escrito como va en el .env, para /copia
  backup.py      el zip con la base de datos, para /backup
  ajustes.py     lo que tienes puesto en el .env, para /ajustes
  aniversario.py las compras que cumplen años, para el resumen del día
  cuota.py       cuenta las consultas a CoinGecko
  comandos.py    entiende lo que le escribes
  temas.py       los temas en que se reparte /ayuda
  lenguaje.py    frases sin barra, como "avísame si btc baja de 60000"
  respuestas/    lo que contesta a cada comando, por temas
    base.py          lo que comparten todos
    mercado.py       /precio, /top, /miedo, /dominancia...
    analisis.py      /rsi, /macd, /soporte, /racha...
    cartera.py       /compra, /venta, /impuestos, /rentabilidad...
    alertas.py       /alerta, /vigilar, /stop, /escalera...
    resumenes.py     el resumen del día, la semana, el mes y el año
    recordatorios.py /recordar, /pienso y /prediccion
    revisiones.py    los avisos del ciclo aparte de los de precio
    comparaciones.py /equivale y los «cuántos X te da tu cartera»
    datos.py         /exportar, /backup y /rellenar
    ratos.py         /horoscopo, /bola, /quiz...
main.py          el ciclo, el bucle de Telegram y la lista de comandos
tests/           los tests
windows/         para dejarlo corriendo en un servidor Windows
linux/           lo mismo en un servidor Linux, con systemd
Dockerfile       la imagen, y docker-compose.yml para arrancarla
```

Pasar los tests y el linter (instala las versiones fijadas en `pyproject.toml`):
```
pip install -e ".[dev]"
pytest
ruff check .
```

En GitHub se pasan solos en cada push, con Python 3.10 y 3.14.
