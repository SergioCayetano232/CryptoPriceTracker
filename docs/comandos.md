# Comandos y uso

[← Volver al README](../README.md)

El bot entiende más de 200 comandos. No hace falta aprendérselos: con
`/ayuda` te los enseña por temas y `/ayuda alerta` te da ejemplos de uno.

**Mirar los precios una vez:**
```
python main.py
```

**Dejarlo vigilando:**
```
python main.py --loop
```
Se queda mirando los precios cada cinco minutos y medio. Para pararlo, `Ctrl+C`.

La primera vez que lo lanzas no te avisa de nada, solo apunta los precios.
Necesita saber dónde estaban antes para saber si han cruzado algo.

Al arrancar te manda un 🟢 *Encendido* con lo que vigila, cuántas alertas tienes
puestas y, si llevaba un rato parado, desde cuándo. Así sabes si el servidor se
ha reiniciado.

Si pasa media hora sin poder consultar los precios, te avisa por Telegram, y
otra vez cuando vuelve a funcionar. Si se para por errores, también te lo dice.
Y si una cripto de `WATCHLIST` no existe en CoinGecko (un `bitcion`), te avisa
una vez al arrancar para que no te quedes esperando un aviso que nunca llegará.

**Manejarlo desde Telegram:**

Mientras está en modo `--loop` puedes escribirle al bot desde el móvil:

| Comando | Qué hace |
|---|---|
| `/status` | Cómo van tus criptos ahora |
| `/hoy` | Cómo van desde las 00:00 en vez de en las últimas 24 h, con el máximo y el mínimo de hoy (`/hoy btc eth`, solo esas). Sale de lo guardado y no gasta consultas |
| `/resumen` | El resumen del día cuando lo pidas, con el índice de miedo y codicia y las compras que cumplen años hoy. No quita el de la hora de siempre |
| `/horario 8:30` | Cambia la hora del resumen del día (y del de los domingos). `/horario no` lo quita; a secas, te dice cuál tienes |
| `/dormir 23-8` | Las horas en que los avisos llegan sin sonar, lo mismo que `HORAS_TRANQUILAS` pero desde Telegram, y manda sobre el `.env`. Vale `/dormir 23:30 7:00` o `/dormir de 0 a 7`. `/dormir no` hace que suenen siempre; a secas, te dice cuáles tienes. También `/tranquilas` |
| `/envivo` | Un mensaje fijado arriba del chat con tus precios y tu cartera, que el bot va editando en cada consulta en vez de mandarte otro. No suena ni gasta consultas. `/envivo no` lo quita; si lo borras tú, deja de actualizarlo solo |
| `/precio solana` | Lo que vale una cripto ahora y cómo va en la última hora, en 24 h, en 7 y en 30 días, aunque no la vigiles, entre qué precios se ha movido en 24 h, lo que vale en sats, cuánto se ha emitido ya de su máximo (si tiene), su máximo histórico con lo que le falta para volver, su puesto por capitalización y cuánto se ha negociado en 24 h (y qué parte es de lo que vale). Debajo, unas barritas `▁▃▅▇` con la forma de las últimas 24 h, si tiene precios guardados. Si la tienes en la cartera, también lo que vale lo tuyo |
| `/precio btc eth sol` | Lo mismo de varias a la vez, una por línea (hasta 10) |
| `/precio` | Sin decir cuál, todas las que vigilas |
| `/precio btc usd` | En otra moneda solo esa vez (`eur`, `usd` o `gbp`; también `$` o `dólares`). Vale con varias y con `/precio usd` a secas. No sale lo tuyo de la cartera, que va en la moneda del `.env` |
| `btc` o `btc eth` | Sin barra, lo mismo que `/precio`. Solo con las conocidas, para que un "hola" no se lo tome como una cripto |
| `@tubot btc` | En cualquier chat, no solo en el del bot: te salen encima del teclado el precio y cómo va en 24 h, y al tocarlo se lo mandas a quien sea. A secas, las que vigilas. Hay que activarlo antes con `/setinline` en @BotFather. Sale de lo guardado y no gasta consultas, así que solo vale con las que vigilas. Solo te contesta a ti y a tus invitados (cada uno, con lo suyo), y a ti solo si `TELEGRAM_CHAT_ID` es tu chat (no un grupo) |
| `avísame si btc baja de 60000` | Algunas frases también las entiende sin barra: «avísame cuando eth suba un 10%» es `/alerta eth +10%`, «avísame si btc baja de 60000 y el miedo está por debajo de 20» es `/alerta btc 60000 si miedo<20`, «cuánto vale sol» es `/precio sol`, «cómo va mi cartera» es `/cartera`, «cállate 2 horas» es `/mute 2h` y «qué sabes hacer» es `/ayuda`. Nunca apunta compras ni ventas así: si lo entendiera mal, te descuadraría la cartera |
| `/ath bitcoin` | Su máximo histórico, cuándo fue y cuánto le falta para volver, y debajo su mínimo histórico y cuánto ha subido desde ahí (vale `/ath btc eth`, solo con el máximo, y a secas, las que vigilas) |
| `/cartera` | Tu cartera: cuánto vale, cuánto ganas o pierdes, el total en sats y la gráfica de 7 días |
| `/cartera 30d` | Lo mismo, con la gráfica del tramo que digas |
| `/cartera usd` | Lo que vale en otra moneda (`eur`, `usd` o `gbp`). Sin lo que ganas ni gráfica, que lo que te costó va en la moneda del `.env` |
| `/reparto` | Qué parte de tu cartera es cada cripto, con una imagen de barras. Si tienes más de 6, las pequeñas van juntas en "Otras" |
| `/tarjeta` | Una imagen cuadrada para reenviar o subir a redes: lo que gana o pierde tu cartera sobre lo que metiste, cómo ha ido en los últimos 30 días (`/tarjeta 90d` para otro tramo) y el reparto. Solo lleva porcentajes, ni una cifra en dinero. También `/compartir` |
| `/rebalanceo btc 60 eth 40` | Qué comprar y qué vender, en dinero y en cantidad, para dejar tu cartera con ese reparto. Lo que tienes y no nombras, a venderlo entero. A secas, a partes iguales entre lo que tienes. Al precio de ahora y sin comisiones. También `/rebalancear` |
| `/ideal btc 60 eth 40` | Guarda el reparto que quieres y te avisa una vez cuando alguna cripto se aleje 5 puntos de lo suyo (con `margen 10` al final, a los que digas), con el `/rebalanceo` para volver listo para copiar. No repite hasta que lo arregles al menos a medias. A secas, cómo vas contra tu reparto, sin gastar consultas; `/ideal no` lo quita |
| `/riesgo` | Cuánto pesa tu cripto más grande y lo que caería la cartera si esa cae un 20%, a cuántas criptos a partes iguales equivale tu reparto, cuánto se mueve la cartera al día en los últimos 30 días (en % y en dinero), su peor día, si se mueve más o menos que bitcoin, y un nivel: bajo, medio o alto |
| `/sharpe 90d` | Cuánto gana tu cartera para lo que se mueve: lo que ha ganado en esos días, lo que se mueve al año, con una nota (de 1 para arriba está bien) y comparado con bitcoin. Con lo que tienes hoy y sin restar lo que daría un depósito. Sin tramo, 90 días; de 30 a 365. Necesita 31 días seguidos guardados |
| `/futuro 30d` | Entre qué cifras puede estar tu cartera dentro de esos días: dónde cae 2 de cada 3 veces y dónde 9 de cada 10, según cuánto se ha movido en los últimos 90 días con lo que tienes hoy. No es una predicción: no dice si sube o baja, solo cuánto suele moverse. Sin tramo, 30 días; hasta 365. Necesita 15 días seguidos guardados. También `/proyeccion` |
| `/semana` | El resumen de tu semana sin esperar al domingo. No gasta consultas |
| `/semana bitcoin` | La semana de una sola: lo mismo que `/historico bitcoin 7d` |
| `/panel` | Un botón que abre el panel web dentro de Telegram, solo para ti. Necesita `PANEL_URL` en el `.env` (ver [el panel](panel.md)) |
| `/enlace` | Un enlace para enseñar tu cartera a quien quieras: solo porcentajes, sin cantidades ni dinero, y caduca en 24 h. Necesita `PANEL_URL` y el panel en marcha |
| `/resumenia` | Tu semana contada en cuatro frases por Claude: cuánto ha cambiado, qué cripto la ha movido más y algo que llame la atención del reparto. Necesita `ANTHROPIC_API_KEY` en el `.env` (cada resumen cuesta céntimos). Solo le manda a Claude el valor de tu cartera, los cambios de la semana y el peso de cada cripto |
| `/mes` | Cómo va tu cartera desde el día 1 del mes, con gráfica, no en los últimos 30 días como `/cartera 30d`. No gasta consultas. También `/mensual` |
| `/anual` | Lo mismo desde el 1 de enero, para compararlo con la bolsa. Con `HISTORY_DAYS=90`, que es lo que viene, a partir de abril no tiene el año entero y te lo dice: pon `366`. También `/año` y `/ytd` |
| `/anual 2025` | Tu resumen de ese año: la cartera, la mejor y la peor cripto, el mejor y el peor mes, compras, ventas, lo ganado vendiendo y tu mejor y peor compra. Te llega solo el 1 de enero si tienes resumen diario, con un botón para pedirlo en imagen |
| `/anual 2025 tarjeta` | Tu año en una imagen cuadrada para enseñar, solo con porcentajes: el % de la cartera, los 12 meses en verde y rojo, la que mejor fue, el mejor mes, cuántas compras y ventas y tu mejor compra. Si solo hay precios desde mitad de año, lo pone. `/anual tarjeta` a secas, la del año en curso |
| `/compra bitcoin 0.01 600` | Apunta en la cartera que has comprado 0,01 por 600 € |
| `/compra bitcoin 0.01 @60000` | Lo mismo, con el precio de cada una en vez del total |
| `/compra bitcoin 0.01 600 com 1.5` | Con la comisión al final, en dinero o en % (`com 0.1%`). En la compra se suma a lo que te costó; en `/venta ... com 1`, se resta de lo que te dieron. Así `/ganancias` e `/impuestos` salen con lo que pagaste de verdad |
| `/compra bitcoin 0.01 600 por el halving` | Con una nota al final de por qué compras (o vendes). Sale en `/movimientos` y en `/compras`, junto a cómo ha salido |
| `/limite 300` | Lo que te permites comprar al mes. Al apuntar una `/compra`, si pasas del 80 % te dice lo que te queda, y si te pasas, por cuánto. A secas, lo que llevas este mes con una barra; `/limite no` lo quita. Las recompensas no cuentan. Se guarda en la base de datos, no en el `.env`. También `/presupuesto` |
| `/venta bitcoin 0.005 350` | Apunta una venta y lo que te dieron (`/venta bitcoin todo` la saca de la cartera) |
| `/ganancias` | Lo que has ganado o perdido de verdad con lo que ya vendiste |
| `/arrepentido` | Lo que valdría hoy lo que vendiste contra lo que te dieron, cripto a cripto, para saber si hiciste bien en vender. Gasta una consulta |
| `/impuestos` | Lo que le tocaría a Hacienda de lo que ganaste vendiendo este año, tramo a tramo (19, 21, 23, 27 y 30 %). `/impuestos 2025`, el año que digas. Va con FIFO, como Hacienda: lo primero que compraste es lo primero que vendes (lo del `PORTFOLIO` del `.env` cuenta como lo más viejo). Por eso puede no coincidir con `/ganancias`, que va con precio medio. Es orientativo |
| `/impuestos 2025 csv` | Te manda un CSV con cada venta de ese año: fecha, cripto, cantidad, valor de transmisión (lo que te dieron, sin la comisión), valor de adquisición (lo que costó, con FIFO y las comisiones de compra) y la ganancia, con el total al final. Es lo que pide la Renta en las ganancias por transmisión de monedas virtuales. Sin año, el de este. Las ventas sin precio van sin cifras y fuera del total |
| `/informe 2025` | El año fiscal en un PDF para guardar o darle al gestor: cuántas ventas, valor de transmisión y de adquisición, la ganancia, lo que le tocaría a Hacienda tramo a tramo, las recompensas y las comisiones, una gráfica de lo ganado cada mes y otra por cripto, y detrás la tabla con cada venta. Con FIFO. A secas, el de este año. Es orientativo |
| `/comisiones` | Lo que llevas pagado en comisiones, en dinero y en % de lo que moviste, por año y por cripto. `/comisiones 2025`, solo ese año. Cuentan las que pones con `com` en `/compra` y `/venta`; las apuntadas antes de esta versión no guardaban la comisión aparte y no salen. También `/fees` |
| `/sivendo btc 0.5` | Lo que te darían, lo que le sacarías y lo que le tocaría a Hacienda, contando lo que ya llevas ganado este año. No apunta nada. También `/sivendo btc todo` y `/sivendo btc 0.5 @80000`, a ese precio |
| `/permuta btc eth 0.01` | Lo que le tocaría a Hacienda si cambias una cripto por otra: en España cuenta como venderla, aunque no veas un euro. Te dice cuánta te darían de la otra, lo que le sacarías y a qué precio contará la nueva cuando la vendas. No apunta nada. También `/permuta btc eth todo` y con `com 0.1%` al final, la comisión. También `/swap` |
| `/compensar` | Si llevas ganancia este año, qué vender de lo que va en pérdidas y cuánto, para bajar lo que le toca a Hacienda y cuánto te ahorrarías. Va con FIFO: si para llegar a lo que pierde hay que vender antes lo que gana, lo cuenta. No apunta nada y tiene que hacerse antes del 1 de enero. Es orientativo y sin comisiones. Si tienes resumen diario, te llega solo en diciembre cuando hay algo que ahorrar. También `/perdidas` |
| `/modelo721` | Si te toca presentar el modelo 721, el de las criptos en exchanges de fuera de España: pasa si a 31 de diciembre valen más de 50.000 €. Del 1 de enero al 31 de marzo te dice lo que valía tu cartera ese día y cuánto te queda de plazo; el resto del año, cuánto le falta para el límite. No sabe dónde tienes cada cripto, así que mira la cartera entera. Con `AVISO_721=si` te avisa una vez al año al pasar de 50.000 €. También `/721` |
| `/primera` | Tu primera compra, cuánto hace, cuánto ha cambiado el precio desde entonces y lo que vale hoy lo que compraste (`/primera btc`, la primera de esa). Solo las apuntadas con `/compra` |
| `/pelotazo` | Tu mejor compra y la peor: lo que pagaste, cuándo, lo que valen hoy y cuánto han subido o bajado. Gasta una consulta |
| `/apodo` | Un mote según cómo llevas la cartera: 🧻 Manos de papel si vendes más de lo que compras, 💎 Manos de diamante si llevas un año sin vender, 🟠 Maximalista si solo tienes bitcoin, 🏔️ Comprador de picos si vas por debajo del -50%... También `/mote` |
| `/hodl` | Cuántos días llevas sin vender cada cripto de tu cartera, de la que más a la que menos: desde la última venta o, si nunca vendiste, desde la primera compra. Si lo vendiste todo y volviste a comprar, cuenta desde la nueva compra. También `/diamante` |
| `/record` | Lo máximo que ha valido tu cartera con los precios guardados, qué día fue y cuánto le falta para volver. Ojo: es lo que tienes hoy a los precios de entonces, no lo que tenías ese día. No gasta consultas. También `/pico` |
| `/vsbtc` | Lo que vale hoy lo que has comprado por Telegram, contra haber metido ese mismo dinero en bitcoin los mismos días (y sacado lo mismo al vender). Usa el precio de bitcoin que tiene guardado, así que necesita llevar vigilándolo desde tus compras. Lo del `PORTFOLIO` del `.env` no cuenta, porque no lleva fecha. También `/vsbitcoin` |
| `/vsbolsa` | Tu cartera contra haber metido lo mismo en la bolsa, en las mismas fechas: lo que vale hoy lo que compraste y lo que valdría en un indexado del S&P 500, y quién gana. Con `/vsbolsa world`, contra el MSCI World. Va con ETF que reinvierten los dividendos (SXR8 y EUNL en euros, CSPX e IWDA en dólares), al cierre de cada día, con los precios de Yahoo. Solo cuenta lo apuntado con `/compra` y `/venta` con precio. También `/bolsa` |
| `/deposito 3%` | Lo que vale hoy lo que has comprado por Telegram, contra haber tenido ese mismo dinero en un depósito al 3 % al año, en las mismas fechas (y sacado lo mismo al vender), con lo que habría puesto de intereses. Debajo, qué interés tendría que dar el depósito para empatar con tu cartera. Sin decir el %, un 3 %. Sin impuestos ni en uno ni en otro. También `/banco` |
| `/inflacion` | Si tu cartera le gana a la subida de precios en España: cuánto han subido desde tu primera compra, cuánto haría falta hoy para comprar lo mismo que con lo que pusiste (cada compra y venta con la inflación desde su fecha) y si lo que te queda vale más o menos, en % de poder de compra. Con el IPCA de España de Eurostat, que sale con uno o dos meses de retraso. Solo cuenta lo apuntado con `/compra` y `/venta` con precio. También `/ipc` |
| `/timing` | Si aciertas el momento de comprar: cada compra contra la media de los 15 días de antes y de después, que es lo que te habría costado comprar un día cualquiera de esas semanas. Te dice cuántas fueron más baratas, cuánto menos (o más) pagaste en total, en qué punto de lo que se movió compraste (0 el día más barato, 100 el más caro), la mejor y la peor. Con `/timing btc`, solo las de esa. Gasta una consulta por cripto y llega hasta un año atrás. También `/momento` |
| `/compras` | Tu mejor y tu peor compra, con el % y lo que va ganando o perdiendo cada una a precio de hoy, y cuántas van en verde. Con `/compras btc`, solo las de esa. Solo las apuntadas por Telegram con lo que costaron |
| `/rentabilidad` | Lo que has metido, sacado y te queda, lo que ganas en total y cuánto sale **al año**, contando cuándo entró y salió cada euro (la TIR, como en los fondos). Con menos de un mes no lo pasa a anual. Solo lo apuntado por Telegram con precio. También `/tir` |
| `/movimientos` | Tus últimas compras y ventas, con un botón para deshacer la última (`/movimientos btc`, solo las de esa) |
| `/recompensa eth 0.02` | Apunta staking o un airdrop, al precio de ahora. Si te llegó antes, `/recompensa eth 0.02 50`, con lo que valía entonces. Se suma a lo que te costó, pero no cuenta como dinero metido en `/rentabilidad` ni en `/vsbtc` |
| `/deshacer` | Quita la última compra o venta y deja la cripto como estaba |
| `/corregir 12 importe 700` | Cambia la cantidad o el importe de una compra, venta o recompensa antigua y rehace las cuentas de las que van detrás. El número sale en `/movimientos` y en `/exportar movimientos`. No deja hacerlo si una venta posterior se queda sin saldo |
| `/emociones` | Con qué ánimo compras y vendes (tranquilo, aburrido, miedo, FOMO o euforia) y cómo te ha ido con cada uno: lo que valen hoy las compras de cada ánimo y lo que valdría hoy lo que vendiste. Con dos o más de al menos dos ánimos, te dice con cuál compras mejor y con cuál peor. El ánimo se apunta con los botones que salen debajo de cada `/compra` y `/venta`, o a mano con `/emocion 12 miedo` (el número sale en `/movimientos`) |
| `/herencia` | Un papel para tu familia en un `.txt`, para guardarlo o imprimirlo: lo que tienes, cuánto vale hoy y dónde está cada una, con una nota tuya y qué hacer para recuperarlo (exchanges, carteras propias, estafas, impuesto de sucesiones). Dónde está cada una se apunta con `/herencia btc Ledger en el cajón del escritorio` y la nota con `/herencia nota ...`. **Nunca guarda claves:** si lo que escribes parece una frase de recuperación o una clave privada, no lo apunta. También `/legado` |
| `/fantasma compra btc 200` | Una cartera de mentira para probar estrategias sin arriesgar: empiezas con 1.000 sin invertir y compras y vendes a precio de ahora (`/fantasma vende btc 50%`, `todo` o un importe). `/fantasma` a secas, cómo va cada una, el total y si le ganas a haber dejado todo en bitcoin el primer día. `/fantasma reinicia 5000` empieza de cero con otra cifra. Sin comisiones. También `/simulador` |
| `/prediccion btc 70000` | Dices a cuánto estará el domingo a las 20:00 y ese día te digo cómo ha quedado: cuánto te fuiste, si acertaste hacia dónde iba y si le ganas a decir «se queda igual». Lleva tu marcador de todas las semanas y, a partir de cuatro, te dice si lo haces mejor que una moneda al aire. Se puede cambiar hasta un día antes. `/prediccion` a secas, lo que tienes en juego y el marcador; `/prediccion btc no`, la quita. También `/apuesta` |
| `/liga` | La clasificación de `/prediccion` entre tú y la gente a la que has invitado: un punto por acertar si sube o baja y otro por acercarte más que decir «se queda igual». A igualdad de puntos, gana quien menos se va. Solo se ven los nombres y los puntos, no lo que tiene nadie. `/liga semana`, solo la del último domingo |
| `/encuesta` | Cada lunes te manda una encuesta de Telegram con dónde estará el domingo la primera cripto que vigilas, en cuatro tramos de un 5%. Lo que votes se apunta como tu `/prediccion` de esa semana, con el centro del tramo, y cuenta para tu marcador y para la `/liga`. Se cierra sola un día antes del domingo; si retiras el voto, se quita la predicción. Al ponerla te manda ya la primera. No gasta consultas. `/encuesta no` la quita |
| `/pienso btc 500` | Antes de comprar: te dice cómo está ahora (lo que ha subido en 24 h, el miedo y codicia y el RSI) y a las 24 h te pregunta si sigues queriendo, con el precio de entonces y un botón ✅ que la apunta en la cartera, o ❌ para dejarlo. `/pienso` a secas, lo que te estás pensando; `/pienso btc no`, lo olvida |
| `/tesis sol el ETF lo va a subir` | Apunta por qué compras, con el precio de ese momento. A los 30 días (o los que digas: `/tesis btc 90d ...`) te la recuerda con el precio de entonces y te pregunta con dos botones si se cumplió. `/tesis` a secas enseña las que esperan y cuántas aciertas. El precio no decide por ti: puedes acertar en el porqué y que baje igual |
| `/recordar lunes 50 btc` | Cada lunes, a la hora del resumen (o a las 9:00 si no tienes), te recuerda tu compra con el precio y lo que te dan los 50 €, y un botón ✅ que la apunta en la cartera. `/recordar` a secas, los que tienes; `/recordar btc no`, lo quita |
| `/alerta bitcoin 70000` | Te avisa una vez cuando llegue a ese precio |
| `/alerta bitcoin +10%` | Te avisa una vez cuando suba un 10% desde ahora |
| `/alerta bitcoin 70000 7d` | Lo mismo, pero si en 7 días no ha llegado se borra sola y te lo dice |
| `/alerta bitcoin 70000 vender la mitad` | Con una nota detrás, que te sale en el aviso (también después del tramo) |
| `/alerta btc 60000 si miedo<20` | Solo salta si además se cumple otra cosa: el índice de miedo (`miedo<20`, `miedo>75`) o el RSI de esa cripto (`rsi<30`, `rsi>70`). Si llega al precio antes, espera a que se cumpla lo otro, y en `/alertas` sale con un 🔗. También vale `y el miedo por debajo de 20`. Con la cartera, solo el miedo |
| `/alerta bitcoin` | Sin precio, te dice a cuánto está y te pone un ejemplo |
| `/alerta cartera 5000` | Lo mismo con lo que vale tu cartera entera (también `-10%`). Si espera a que suba, con una barra `▓▓▓▓░░` de lo que llevas |
| `/escalera btc 80000 90000 100000` | Para vender por tramos al subir en vez de todo de golpe: reparte lo que tienes a partes iguales entre los precios (de 2 a 10) y te dice cuánto vender en cada uno, cuánto cobrarías, lo que ganarías y lo que le tocaría a Hacienda con FIFO. Con `50%` al final, solo reparte la mitad. Cada escalón es una `/alerta` con la cantidad en la nota, así que sale en `/alertas` y se quita con `/quitar`. No vende nada |
| `/escalera compra btc 60k 55k 50k con 900` | Lo mismo al revés, para comprar por tramos cuando baja: reparte lo que vas a meter entre los precios, te dice cuánto compras en cada uno y a qué precio medio te quedas, contando lo que ya tenías. Sin `con 900` solo pone los avisos. No hace falta tener cartera. No compra nada |
| `/stop eth -15%` | Te avisa una vez si pierdes un 15% sobre tu precio medio, no sobre el precio de ahora. Si compras o vendes, se mueve solo a tu nuevo precio medio. Con `+50%`, al ganar. `/stop cartera -20%` lo mira con todo lo que metiste. Con `/stop btc -10% movil`, te avisa si cae un 10% desde lo más alto que toque desde que lo pones: si sube, el aviso sube con ella. Sale en `/alertas` y se quita con `/quitar` |
| `/alertas` | Las alertas que tienes puestas y cuánto le falta a cada una, la más cerca primero, con un 🗑 para quitarlas |
| `/ultimo` | Cuándo te avisó por última vez cada una de las que vigilas, a qué precio y cuánto se ha movido desde entonces. Solo cuenta los avisos que llegaron, no los del silencio |
| `/quitar 3` | Quita la alerta número 3 (`/quitar 2 5` varias, `/quitar bitcoin` las de esa cripto, `/quitar todas` todas) |
| `/volatilidad bitcoin 30d` | Cuánto se mueve de media al día y cuántos avisos te habría dado `/vigilar` con %2, %5 y %10 (sin tramo, 30 días) |
| `/ruido` | De los avisos que te habrían dado tus reglas de `/vigilar`, cuántos fueron en falso: en las 24 h siguientes el precio volvió a cruzar la línea (o, en los de %, deshizo la mitad del movimiento). Si más de un tercio lo son, te propone el % o el paso más pequeño que lo arregla, listo para copiar (si vigilas por pasos y ninguno más ancho vale, prueba con %). Con `/ruido bitcoin 90d`, solo una y en otro tramo (sin tramo, 30 días). Sale de lo guardado y no gasta consultas. También `/falsos` |
| 👍 y 👎 en los avisos | Debajo de cada aviso de lo que vigilas hay dos botones para decir si te sirvió o sobraba. Se guarda uno por aviso (si pulsas el otro, cambia) y `/ruido` los enseña: si te sobran más de la mitad, te propone una regla más ancha aunque el precio no lo viera como ruido. No salen en las `/alerta` ni cuando el aviso junta varias criptos |
| `/vigilar` | Lo que está vigilando y cómo, con un ✖ en cada una para dejarla |
| `/vigilar solana %5` | Añade una cripto, o cambia cómo vigila una que ya estaba |
| `/dejar solana` | Deja de vigilarla (`/dejar sol eth` varias a la vez) |
| `/historico bitcoin` | Imagen con la gráfica de las últimas 24 h, máximo y mínimo |
| `/historico bitcoin 7d` | Lo mismo, del tramo que digas (`12h`, `7d`, `30d`...) |
| `/historico` | Sin decir cuál, la primera que vigilas (también `/historico 7d`) |
| `/historico bitcoin 7d velas` | En velas: cada una con la apertura, el máximo, el mínimo y el cierre de su rato (1 hora hasta 48 h, 4 horas hasta 10 días y 1 día en adelante), verde si cerró por encima de donde abrió. Las velas van seguidas aunque falten días por medio. Debajo de cada gráfica hay un botón para pasar de línea a velas y al revés |
| `/media bitcoin` | Su media de 7, 30 y 90 días y si el precio de ahora está por encima o por debajo de cada una, y si lo está de todas (`/media bitcoin 14d`, solo la de esos días). Sale de lo guardado y no gasta consultas |
| `/racha bitcoin` | Cuántos días seguidos lleva subiendo o bajando y cuánto lleva en esa racha. Sale de lo guardado y no gasta consultas |
| `/racha cartera` | Lo mismo con tu cartera entera, con lo que tienes hoy a los precios del final de cada día |
| `/extremo bitcoin 30d` | El día que más subió y el que más bajó en ese tramo, con la fecha y hace cuánto fue, el % y de qué precio a cuál (sin tramo, 30 días). Sale de lo guardado y no gasta consultas |
| `/verdes bitcoin 30d` | Cuántos días subió y cuántos bajó en ese tramo, qué parte fue en verde y cómo fueron los últimos 7 en cuadraditos 🟩🟥 (sin tramo, 30 días). Sale de lo guardado y no gasta consultas |
| `/calendario btc` | Una imagen del mes con cada día en verde o en rojo, más fuerte cuanto más se movió, y su %. Debajo, cuántos días subió y bajó, el mejor, el peor y el total del mes. Con `/calendario btc octubre`, un mes pasado. No gasta consultas |
| `/diasemana bitcoin 90d` | Lo que sube o baja de media cada día de la semana, cuál suele ser el mejor y el peor, y cómo suele ir el de hoy (sin tramo, 90 días). Sale de lo guardado y no gasta consultas |
| `/diames bitcoin` | Qué día del mes ha salido más barata y cuál más cara, comparando cada día con la media de las dos semanas de antes y de después (así una subida de fondo no hace que el día 1 salga siempre el más barato), y si sale mejor comprar a principio, a mitad o a final de mes. Para elegir el día de una compra mensual. Sin tramo, el último año; necesita al menos un mes seguido guardado. Con `HISTORY_DAYS=90`, que es lo que viene, solo hay tres meses: pon `366` o usa `/rellenar`. Sale de lo guardado y no gasta consultas |
| `/estacional btc` | Qué meses del año suele subir y cuáles bajar: lo que hace cada mes del primer día al último (la mediana, para que un año loco no lo tape todo) y cuántos años subió, con el mejor y el peor. Va con las velas mensuales de Binance desde 2017, en dólares, así que no depende de lo guardado ni gasta consultas de CoinGecko. A secas, la primera que vigilo. También `/meses` |
| `/ciclo` | Lo que dicen a la vez los indicadores de largo plazo de bitcoin: Mayer, arcoíris, 200 semanas, Pi Cycle, ahr999, MVRV y hash ribbons. Cada uno dice barato, caro o en medio, y si ganan por dos o más los de un lado, dice si está cerca de un fondo o de un techo de ciclo; si no, a mitad de ciclo. Como `/semaforo`, pero para el ciclo y no para estos días. Si una fuente falla sigue con las demás y dice cuáles faltan. Los cinco primeros salen de una sola descarga de Binance. También `/ciclos` |
| `/mayer` | El múltiplo de Mayer de bitcoin: su precio entre su media de 200 días. Por debajo de 1 está más barato que de media en los últimos siete meses; por encima de 2,4 solía ser burbuja. Dice en qué zona está, qué parte de los días desde 2017 estuvo más bajo que hoy, lo más alto y lo más bajo que ha llegado, con una barrita del último año, y a qué precio volvería a su media y a qué precio entraría en burbuja. Va con las velas diarias de Binance desde 2017, en dólares, así que no depende de lo guardado ni gasta consultas de CoinGecko. `/mayer eth` lo saca de otra, aunque se pensó para bitcoin. También `/multiplo` |
| `/arcoiris` | La gráfica arcoíris de bitcoin: su precio desde 2017 encima de nueve franjas de colores, de «Saldo: casi regalado» a «Burbuja máxima», en escala logarítmica y con un año más hacia delante. Dice en qué franja está hoy, cuánto se separa de su curva de largo plazo y a qué precios cambiaría de franja. La curva la ajusta él con los precios diarios de Binance (una ley de potencias: el precio frente a los días desde el primer bloque) y las franjas reparten a partes iguales entre lo más bajo y lo más alto que ha estado, así que con los años se mueve un poco. Es un dibujo, no una predicción. No gasta consultas de CoinGecko. También `/rainbow` |
| `/suelo` | Bitcoin frente a su media de 200 semanas, unos cuatro años: un ciclo entero. Ha ido a tocarla en el fondo de cada ciclo, así que se usa como suelo. Dice a qué distancia está, con una barrita del último año, cuántas semanas ha cerrado por debajo desde 2021, lo más lejos y lo más abajo que ha llegado, cuánto ha subido la media en un año y a qué precio la tocaría. Va con las velas diarias de Binance en dólares, así que no gasta consultas de CoinGecko. También `/200semanas` y `/200w` |
| `/mvrv` | El MVRV de bitcoin: su precio entre el precio realizado, que es lo que costó cada bitcoin la última vez que se movió (lo que pagaron de verdad los que lo tienen). Dice cuánto ganan de media los que tienen bitcoin, el Z-score con una barrita del último año, en qué zona está (por debajo de 0 fueron los fondos y por encima de 7, los techos de 2013 y 2017), a qué precio bajaría a 0 y lo más alto y lo más bajo desde 2012. Los datos son de la API gratuita de CoinMetrics, con un día de retraso. También `/realizado` y `/zscore` |
| `/picycle` | El Pi Cycle Top de bitcoin: la media de 111 días contra el doble de la de 350. Cuando la primera pasa por encima de la segunda, bitcoin solía estar en su techo (2013, 2017 y abril de 2021, aunque no avisó del de noviembre de 2021). Dice cuánto le falta a la rápida para cruzarse, con una barrita del último año, y cada vez que se han cruzado desde 2018, con cuándo llegó el máximo. Va con las velas diarias de Binance en dólares y no gasta consultas de CoinGecko. También `/pi` y `/techo` |
| `/ahr999` | El índice ahr999 de bitcoin: si toca comprar fuerte (por debajo de 0,45), comprar poco a poco (hasta 1,2) o esperar. Multiplica el precio entre lo que costó comprar a diario los últimos 200 días por el precio entre lo que debería valer según una curva de crecimiento. Dice la zona, con una barrita del último año, los precios a los que cambiaría de zona, qué parte de los días desde 2018 estuvo más bajo y la última vez en zona de comprar fuerte. La curva es la que publicó su autor en 2019, sin reajustar, para que la cifra cuadre con la de las webs; desde 2022 va bastante por encima del precio, así que ahora sale más bajo que antes. Va con las velas diarias de Binance en dólares. También `/ahr` |
| `/paciencia` | Si hubieras comprado bitcoin un día cualquiera desde 2017, cuántas veces ganabas aguantando 1 mes, 6 meses, 1 año, 2, 3 y 4 años, con lo típico (la mediana) de cada plazo. Dice si alguien que aguantó el plazo más largo llegó a perder, cuál fue el peor día para comprar y cuánto irías ganando si hubieras comprado justo hace ese plazo. `/paciencia eth` lo mira con otra. Va con las velas diarias de Binance en dólares. También `/aguante` |
| `/cme` | El hueco del fin de semana en los futuros de bitcoin del CME, que paran del viernes por la tarde al domingo por la noche (hora de Nueva York). Dice a cuánto cerró el viernes y abrió el domingo, si el hueco ya se cerró y cuándo, o a qué precio tendría que volver. Si es fin de semana, cuánto hueco quedaría si abriera ahora. Lista los de las últimas semanas que siguen abiertos y cuántos se cerraron. Va con las velas de una hora de Binance, no con el precio del CME, y no cuenta los festivos, así que es aproximado. También `/hueco` y `/gap` |
| `/dvol` | El DVOL de bitcoin, el índice de volatilidad de las opciones de Deribit: lo que el mercado espera que se mueva en un año, como el VIX de la bolsa. Dice si está tranquilo o nervioso comparado con su último año, con una barrita, cuánto ha cambiado en una semana, lo más alto y lo más bajo del año, y lo que eso supone en ± % para un día, una semana y un mes. `/dvol eth` para ethereum, que son las dos que tiene Deribit. No pide clave ni gasta consultas de CoinGecko. También `/vix` y `/opciones` |
| `/maxpain` | Las opciones de bitcoin que vencen este viernes en Deribit y su *max pain*: el precio de vencimiento con el que menos cobran los que las compraron, al que se dice que el precio tiende a acercarse los días antes. Dice cuánto vence (en BTC y en dólares), a qué distancia está el precio, cuántos puts hay por cada call, en qué precio hay más calls y más puts y, si hay otro vencimiento más gordo por delante, cuándo es y su max pain. `/maxpain eth` para ethereum. No pide clave. También `/vencimiento` y `/dolor` |
| `/horas bitcoin 30d` | A qué hora del día suele estar más barata y a cuál más cara, comparando cada hora con la media de su día, con una barrita de las 24 horas y cómo suele estar a la hora de ahora (sin tramo, 30 días). Solo cuenta los días que tiene casi enteros. Sale de lo guardado y no gasta consultas |
| `/rango bitcoin 30d` | Su máximo y su mínimo en ese tramo con hace cuánto fueron, su media y en qué punto del rango está hoy (sin tramo, 7 días). Sale de lo guardado y no gasta consultas |
| `/soporte bitcoin 90d` | Los precios donde ha girado al menos dos veces: hasta 3 resistencias por arriba y 3 soportes por abajo, el más cercano primero, con cuántas veces lo ha tocado, la última y a cuánto está. Un giro es el máximo o el mínimo de un día comparado con los dos de antes y los dos de después; los que quedan a menos de un 2 % cuentan como el mismo. Sirve para poner alertas con sentido. Sin tramo, 90 días. Sale de lo guardado y no gasta consultas. También `/resistencia` |
| `/dia bitcoin 01/09` | Qué día de la semana fue, a cuánto cerró, su máximo y su mínimo, y cuánto ha cambiado desde entonces. Vale `ayer` y con año (`01/09/2025`). Sale de lo guardado y no gasta consultas |
| `/cuando bitcoin 60000` | La última vez que estuvo a ese precio (o más abajo, si ahora está por encima), hace cuánto y lo que ha cambiado desde entonces. Vale `60k`. Sale de lo guardado y no gasta consultas |
| `/redondo bitcoin` | Cuánto le falta para la siguiente cifra redonda por arriba y por abajo (de 64.000 a 70.000 y a 60.000). A secas, las que vigilas. Sale de lo guardado y no gasta consultas |
| `/semaforo bitcoin` | Una sola luz, verde, ámbar o roja, que junta lo que dicen el RSI, el MACD, las bandas de Bollinger, las medias, el índice de miedo y el funding: cada uno vota a favor de comprar, en contra o en medio, y hace falta ganar por dos para salir del ámbar. Debajo, el voto de cada uno con su porqué. No es un consejo. No gasta consultas de CoinGecko |
| `/rsi bitcoin` | Su RSI de 14 días: por encima de 70 ha subido demasiado rápido (sobrecomprada) y por debajo de 30 ha bajado demasiado (sobrevendida). Necesita 15 días seguidos guardados y no gasta consultas |
| `/bollinger bitcoin` | Sus bandas de Bollinger: la media de 20 días y dos veces lo que se suele separar de ella, por arriba y por abajo. Te dice si el precio está dentro, por encima (muy estirada) o por debajo (muy aplastada), con una barrita de dónde está, y si la banda está de las más estrechas de lo guardado, que suele ir antes de un movimiento fuerte. Necesita 20 días seguidos guardados y no gasta consultas. También `/bandas` |
| `/macd bitcoin` | Si va con empuje al alza o a la baja según el MACD (la media de 12 días menos la de 26, contra su propia media de 9): desde cuándo, si coge o pierde fuerza y hacia dónde va de fondo. Cruzar su señal hacia arriba se suele leer como compra y hacia abajo como venta, con retraso. A secas, la primera que vigilo. Necesita 35 días seguidos guardados. Sale de lo guardado y no gasta consultas. También `/empuje` |
| `/tormenta` | Lo que se ha movido cada una que vigilas en los últimos 7 días (entre lo más alto y lo más bajo) contra lo que se mueve en una semana normal, y si está «muy quieta»: de las semanas más tranquilas de lo guardado, que se dice que va antes de un movimiento fuerte. Con `/tormenta btc eth`, solo esas. Necesita 38 días guardados y no gasta consultas. También `/squeeze` |
| `/estocastico bitcoin` | Dónde está el precio dentro de lo que se ha movido en 14 días, de 0 (lo más bajo) a 100 (lo más alto): por encima de 80, sobrecompra; por debajo de 20, sobreventa. Con su media de 3 días y si la ha cruzado hace poco. Saca el máximo y el mínimo de cada día de lo que tiene guardado, así que necesita 17 días seguidos: `/rellenar` baja los que faltan. También `/stoch` |
| `/fibonacci btc 90d` | Los niveles de Fibonacci entre el máximo y el mínimo del tramo (23,6%, 38,2%, 50%, 61,8% y 78,6%): si venía subiendo, hasta dónde podría corregir; si venía bajando, hasta dónde podría rebotar. Marca dónde está ahora y el nivel más cerca por debajo y por encima. Sin tramo, 90 días. Sale de lo guardado y no gasta consultas. También `/fibo` y `/retroceso` |
| `/caida bitcoin 30d` | Cuánto ha bajado desde el máximo del tramo y cuál fue su peor caída, de qué precio a cuál y cuánto tardó en volver (sin tramo, 30 días). Con `/caida cartera`, lo mismo con lo que vale tu cartera entera. Sale de lo guardado y no gasta consultas |
| `/backtest btc 20%` | Qué habría pasado si hubieras vendido cada vez que subía un 20% y recomprado cada vez que bajaba un 20% desde la última operación, contra no tocar nada. Empieza con 1.000 € y usa los precios que tiene guardados, 90 días si no le dices otro tramo (`/backtest btc 15% 30d`). Te dice también dónde tocaría la próxima. Sin comisiones ni impuestos |
| `/sube bitcoin 30d` | Lo contrario: cuánto ha subido desde el mínimo del tramo y cuál fue su mejor subida, de qué precio a cuál (sin tramo, 30 días). También con `/minimo`. Sale de lo guardado y no gasta consultas |
| `/comparar btc eth sol 7d` | Qué tal le ha ido a cada una en ese tramo, de la mejor a la peor (sin tramo, 7 días; sin criptos, las que vigilas). Con una gráfica de todas juntas, empezando en el mismo punto para que un BTC de 60.000 y un DOGE de céntimos se puedan comparar. Con más de 6 va sin gráfica, que no se distinguirían las líneas |
| `/quieta` | La que menos se ha movido en las últimas 24 h de las que vigilas, del mínimo al máximo, y debajo las demás. Sale de lo guardado y no gasta consultas |
| `/correlacion btc eth 30d` | Si dos criptos suben y bajan a la vez (de -1 a +1), para saber si tu cartera está repartida de verdad (sin tramo, 30 días; sin criptos, las dos primeras que vigilas). Sale de lo guardado y no gasta consultas |
| `/correlacion todas` | Todas contra todas, las que vigilas y las de tu cartera (hasta 8), en una imagen con un color por casilla: naranja las que van juntas y azul las que van al revés. Debajo, la pareja que más y la que menos, y la media: si pasa de +0,7, tenerlas todas reparte poco el riesgo. Con `90d` al final, otro tramo |
| `/juntas btc eth` | Te avisa una vez cuando dos criptos que siempre van a la vez llevan 10 días cada una por su lado (su correlación baja de 0,3), con lo que se ha movido cada una. Suele ser que a una le pasa algo. No repite hasta que vuelven a ir juntas. Las dos tienen que estar vigiladas o en la cartera; si en el mes ya no van juntas, te lo dice y no la pone. A secas, las que miras; con `no` al final, la quita |
| `/ratio eth btc 30d` | Cuánto vale una en la otra (1 ethereum = 0,03 bitcoin) y cuánto ha cambiado en ese tramo, con barritas, el máximo, el mínimo y en qué punto del rango está. Si sube, a la primera le ha ido mejor (sin tramo, 30 días; sin criptos, las dos primeras que vigilas). Sale de lo guardado y no gasta consultas |
| `/convertir 0.05 bitcoin` | Cuánto es en euros al precio de ahora |
| `/convertir 500 eur solana` | Al revés: cuánta solana compras con 500 € (vale `500€`) |
| `/convertir 1 eth btc` | De una cripto a otra: cuánto bitcoin es 1 ethereum, y al revés |
| `/convertir 100000 sats` | En satoshis (cien millones son un bitcoin). Vale al revés, `/convertir 50 eur sats`, y entre criptos, `/convertir 1 eth sats` |
| `/si 1000 bitcoin 30d` | Cuánto tendrías hoy si hubieras metido 1.000 € hace 30 días (sin tramo, 30 días) |
| `/dca 50 bitcoin semanal 90d` | Lo mismo metiendo 50 € cada semana, con lo invertido y el precio medio. También `diario` o `mensual`; sin decirlo, semanal y 90 días |
| `/objetivo bitcoin 100000` | Cuánto valdría tu cartera si bitcoin llegara a ese precio, y cuánto ganarías sobre lo invertido. Vale `100k`, y también para ver una bajada |
| `/promediar btc 50000` | Cuánto comprar al precio de ahora, en cantidad y en dinero, para que tu precio medio baje a 50.000. Vale `50k`. Si ya te sale más barato, o si pides uno por debajo del precio de ahora (que comprando no se llega), te lo dice. Sin comisiones. También `/promedio` |
| `/posicion 1000 2% -10%` | Cuánto meter para no perder más de un 2 % de tus 1.000 si cae un 10 % y salta el stop: 200. Con la cripto delante, `/posicion btc 1000 2% -10%`, también cuánto bitcoin es y a qué precio poner el stop, y el stop puede ser un precio: `/posicion btc 1000 2% 58000`. Si el stop está tan cerca que puedes meterlo todo, te lo dice. Sin cripto no gasta consultas. También `/tamaño` |
| `/apy eth 4%` | Cuánto ethereum tendrías dejando el de tu cartera en staking al 4 % al año, en 1, 3, 5 y 10 años, y lo que valdría al precio de hoy. Con `/apy 2 eth 4%`, de la cantidad que digas, y con `5a` (o `5 años`) al final, solo a esos años. El APY ya lleva el interés compuesto. Lo cobrado de verdad se apunta con `/recompensa`. También `/interés` |
| `/plan 10000 50 semanal` | Cuánto tardas en llegar a 10.000 metiendo 50 cada semana (también `diario` o `mensual`; sin decirlo, semanal), hacia qué mes y cuánto habrás metido. Cuenta lo que ya vale tu cartera. Con `8%` al final, suponiendo que dé eso al año, y cuánto pone ese interés. No gasta consultas si tiene los precios guardados. También `/ahorro` |
| `/meta 10000` | Cuánto le falta a tu cartera para llegar a esa cifra, en dinero y en %, con una barra de lo que llevas. Vale `10k`. También `/goal` |
| `/equilibrio` | A qué precio dejas de perder con cada cripto de tu cartera y cuánto le falta, de la que más lejos está a la que menos, y cuánto tendría que subir todo junto. Solo con las que dicen lo que te costaron |
| `/doble` | A qué precio tiene que llegar cada cripto de tu cartera para que dobles lo que metiste, cuánto le falta y cuánto tendría que subir todo junto. Solo con las que dicen lo que te costaron |
| `/mitad` | Al revés que `/doble`: a qué precio perderías la mitad de lo que metiste en cada cripto y cuánto puede bajar hasta ahí, la que menos aguanta primero. Solo con las que dicen lo que te costaron |
| `/exportar bitcoin 30d` | Te manda un CSV con los precios guardados (sin tramo, 30 días) |
| `/exportar movimientos` | Te manda un CSV con todas tus compras y ventas, lo que ganaste en cada venta y tus notas |
| `/importar` | Apunta de golpe tus compras y ventas de Binance o de Kraken. Mándale al bot el CSV como archivo: el de Binance sale en Órdenes → Historial de operaciones → Exportar; el de Kraken, exportando las operaciones (Trades), y si llega en un .zip, vale el trades.csv de dentro. Te dice lo que ha leído y lo que se salta (lo que no es contra tu moneda, lo de margen, las criptos que no conoce) y solo apunta al pulsar Importar. Cada una lleva el exchange en la nota y la comisión dentro del importe. No apunta lo que ya tenías apuntado ni lo anterior a tu último movimiento |
| `/binance` | Lo que tienes de verdad en Binance contra lo apuntado en el bot: lo que está sin apuntar, lo que está apuntado y no aparece (puede estar en otro sitio) y lo que cuadra. Cuenta lo bloqueado en órdenes y Simple Earn flexible; futuros y staking bloqueado no. Necesita una clave de **solo lectura** en `BINANCE_API_KEY` y `BINANCE_API_SECRET` del `.env` (sin ella, te explica cómo crearla). El bot solo lee y nunca enseña la clave |
| `/backup` | Te manda un zip con la base de datos entera: precios, compras, ventas y alertas. También `/respaldo` |
| `/rellenar btc 90d` | Baja de CoinGecko los precios pasados que no tiene, para que `/rsi`, `/media`, `/racha` y compañía funcionen sin esperar semanas. Solo mete lo que falta, así que se puede repetir. Sin tramo, todo lo que quepa en `HISTORY_DAYS` (hasta un año); a secas, las que vigilas. Hasta 90 días viene un precio por hora y con más, uno al día. Gasta una consulta por cripto |
| `/mercado` | Lo que vale todo el mercado cripto, cómo va en 24 h y qué parte es de Bitcoin, Ethereum y las estables |
| `/dominancia` | Qué parte de todo el mercado es bitcoin y cuántos puntos ha ganado o perdido en 24 h, 7 y 30 días, para saber si el dinero se va a las altcoins o vuelve a bitcoin. Debajo, la parte de Ethereum, las estables y el resto. CoinGecko solo da la de ahora, así que en `--loop` guarda una foto al día (una consulta más al día) y compara con esas: los primeros días no tiene con qué. También `/altcoins` |
| `/altseason` | Si es temporada de altcoins: cuántas de las 50 más grandes le han ganado a bitcoin en 30 días, de 0 a 100. Con 75 o más es temporada de altcoins y con 25 o menos, de bitcoin. Debajo, las tres que más y las tres que menos, y si alguna de las tuyas le gana. No cuenta estables, oro ni copias de otra (como WBTC o stETH). El índice de siempre mira 90 días, pero CoinGecko solo da 30 en esta consulta, así que este salta antes. Gasta una consulta. También `/temporada` |
| `/halving` | Cuántos días faltan para el próximo halving de Bitcoin, cuánto va de ciclo y cuánto bajará lo que se paga por bloque. La fecha es aproximada y no gasta consultas |
| `/cumple` | Los años de Bitcoin, los días que lleva funcionando y cuánto falta para su cumpleaños (el 3 de enero) |
| `/whitepaper` | Los años del whitepaper de Bitcoin, los días desde que Satoshi lo publicó y cuánto falta para que cumpla (el 31 de octubre) |
| `/merge` | Los años desde The Merge, cuando Ethereum dejó la minería, los días que lleva y cuánto falta para el aniversario (el 15 de septiembre) |
| `/ethereum` | Los años de Ethereum desde que arrancó, los días que lleva, a cuánto salió en la preventa y cuánto falta para su cumpleaños (el 30 de julio) |
| `/adios` | El tiempo que lleva Satoshi sin aparecer desde su último mensaje en el foro (el 12 de diciembre de 2010) y cuánto falta para que se cumpla otro año |
| `/pizza` | Lo que valdrían hoy los 10.000 BTC que se pagaron por dos pizzas en 2010, y cuánto falta para el Bitcoin Pizza Day |
| `/mundo` | Lo que le tocaría a cada persona del mundo si se repartieran los 21 millones de bitcoin, en sats y en dinero al precio de hoy |
| `/millonario` | Cuánto bitcoin (u otra, `/millonario eth`) necesitas para tener un millón al precio de hoy y, si la tienes en la cartera, cuánto llevas del camino |
| `/sat` | Lo que vale un satoshi (la cien millonésima parte de un bitcoin) y cuántos te dan 1, 10 y 100. Para cantidades exactas, `/convertir 50 eur sats` |
| `/lambo` | Cuántos Lamborghinis te da tu cartera, a unos 250.000 cada uno, y cuánto te falta para el siguiente |
| `/enletras` | Lo que vale tu cartera escrito en letras, como en un cheque: «Mil doscientos treinta y cuatro euros con cincuenta céntimos». También `/cheque` |
| `/ballena` | Qué bicho eres según los bitcoin que tienes: gamba (menos de 1), cangrejo, pulpo, pez, delfín, tiburón, ballena (desde 1.000) o ballena jorobada, y cuánto te falta para el siguiente. No gasta consultas |
| `/cafe` | Cuántos cafés te da tu cartera, a 1,50 cada uno, y para cuánto tiempo tienes tomando uno al día |
| `/iphone` | Cuántos iPhone Pro te da tu cartera, a unos 1.500 cada uno, y cuánto te falta para el siguiente |
| `/alquiler` | Cuántos meses de alquiler te paga tu cartera, a unos 1.100 al mes, lo de un piso normal en España |
| `/oro` | Cuántos gramos de oro te da tu cartera, con el precio de hoy (lo saca de PAX Gold, que es una onza por token) |
| `/netflix` | Cuántos meses de Netflix te paga tu cartera, con el plan Estándar a 13,99 al mes |
| `/ps5` | Cuántas PS5 Pro te da tu cartera, a unos 800 cada una, y cuánto te falta para la siguiente. También `/playstation` |
| `/tesla` | Cuántos Tesla Model 3 te da tu cartera, a unos 40.000 cada uno, y cuánto te falta para el siguiente |
| `/spotify` | Cuántos meses de Spotify te paga tu cartera, con el Premium Individual a 11,99 al mes |
| `/cana` | Cuántas cañas te da tu cartera, a unos 3 cada una, y cuántas rondas para cuatro si invitas tú. También `/caña` y `/cerveza` |
| `/switch` | Cuántas Nintendo Switch 2 te da tu cartera, a unos 470 cada una, y cuánto te falta para la siguiente. También `/nintendo` |
| `/cine` | Cuántas entradas de cine te da tu cartera, a unos 9 cada una, y para cuánto tienes yendo una vez por semana. También `/peli` |
| `/gimnasio` | Cuántos meses de gimnasio te paga tu cartera, a unos 40 al mes. También `/gym` |
| `/vuelo` | Cuántos viajes a Nueva York te da tu cartera, a unos 600 ida y vuelta desde Madrid, y cuánto te falta para el siguiente. También `/viaje` y `/avion` |
| `/super` | Cuántos carros de la compra te da tu cartera, a unos 100 cada uno, y para cuánto comes con uno a la semana. También `/supermercado` |
| `/kebab` | Cuántos kebabs te da tu cartera, a unos 6 cada uno, y para cuánto cenas con uno cada viernes. También `/doner` |
| `/metro` | Cuántos meses de abono de transporte te paga tu cartera, a unos 30 al mes. También `/abono` y `/bus` |
| `/luz` | Cuántos meses de factura de la luz te paga tu cartera, a unos 60 al mes. También `/factura` |
| `/libro` | Cuántos libros te da tu cartera, a unos 20 cada uno, y para cuánto tienes leyendo uno al mes. También `/leer` |
| `/concierto` | Cuántas entradas de concierto te da tu cartera, a unos 50 cada una, y cuántos conciertos para dos si invitas tú. También `/musica` |
| `/airpods` | Cuántos AirPods Pro te da tu cartera, a unos 250 cada uno, y cuánto te falta para los siguientes. También `/auriculares` |
| `/zapatillas` | Cuántos pares de zapatillas te da tu cartera, a unos 120 cada par, y cuántos años vas calzado estrenando unas cada temporada. También `/zapas` |
| `/ave` | Cuántos viajes en AVE a Barcelona te da tu cartera, a unos 80 ida y vuelta desde Madrid, y para cuánto tienes con una escapada al mes. También `/tren` |
| `/menu` | Cuántos menús del día te da tu cartera, a unos 13 cada uno, y para cuánto comes fuera de lunes a viernes. También `/comida` |
| `/hotel` | Cuántas noches de hotel te da tu cartera, a unos 100 cada una, y cuántas escapadas de finde son. También `/noche` |
| `/peluqueria` | Cuántos cortes de pelo te da tu cartera, a unos 15 cada uno, y para cuánto vas peinado cortándote una vez al mes. También `/pelo` |
| `/macbook` | Cuántos MacBook Air te da tu cartera, a unos 1.300 cada uno, y cuánto te falta para el siguiente. También `/portatil` y `/mac` |
| `/bici` | Cuántas bicis de carretera te da tu cartera, a unos 800 cada una, y cuánto te falta para la siguiente. También `/bicicleta` |
| `/churros` | Cuántos chocolates con churros te da tu cartera, a unos 4 cada uno, y para cuánto tienes desayunando unos cada domingo. También `/chocolate` |
| `/loteria` | Cuántos décimos de Navidad te da tu cartera, a 20 cada uno, y los días que faltan para el sorteo del 22 de diciembre. También `/lotería` y `/decimo` |
| `/piso` | Cuántos metros cuadrados de piso en Madrid te da tu cartera, a unos 5.500 el m², y cuánto te falta para uno de 70 m². También `/casa` y `/vivienda` |
| `/futbol` | Cuántas entradas de fútbol te da tu cartera, a unos 60 cada una, y para cuántas temporadas tienes yendo a todos los partidos en casa. También `/fútbol` y `/partido` |
| `/taxi` | Cuántos taxis al aeropuerto te da tu cartera, con la tarifa fija de 33 de Madrid a Barajas, y cuántas escapadas son contando ida y vuelta. También `/aeropuerto` y `/cabify` |
| `/tortilla` | Cuántos pinchos de tortilla te da tu cartera, a unos 3 cada uno, y para cuánto tienes con uno cada mañana. También `/pincho` |
| `/videojuego` | Cuántos videojuegos nuevos te da tu cartera, a unos 80 cada uno, y para cuánto tienes comprando uno al mes. También `/juego` y `/juegos` |
| `/sofa` | Cuántos sofás de tres plazas de IKEA te da tu cartera, a unos 500 cada uno, y cuánto te falta para el siguiente. También `/sofá` y `/ikea` |
| `/coche` | Cuántos coches nuevos te da tu cartera, a unos 20.000 un utilitario, y cuánto te falta para el siguiente. También `/coches` y `/auto` |
| `/boda` | Cuántas bodas te da tu cartera, a unos 25.000 una con cien invitados, y cuánto te falta para la siguiente. También `/bodas` y `/casarse` |
| `/jamon` | Cuántos jamones ibéricos te da tu cartera, a unos 500 la pata de bellota, y cuánto te falta para el siguiente. También `/jamón` y `/jamones` |
| `/rolex` | Cuántos Rolex te da tu cartera, a unos 10.000 un Submariner nuevo, y cuánto te falta para el siguiente. También `/reloj` |
| `/aceite` | Cuántos litros de aceite de oliva virgen extra te da tu cartera, a unos 8 el litro, y cuánto te falta para el siguiente. También `/aove` y `/oliva` |
| `/paella` | Cuántas paellas para cuatro te da tu cartera, a unos 60 en un restaurante, y cuánto te falta para la siguiente. También `/paellas` |
| `/croquetas` | Cuántas raciones de croquetas te da tu cartera, a unos 10 la de ocho caseras, y cuánto te falta para la siguiente. También `/croqueta` |
| `/pan` | Cuántas barras de pan te da tu cartera, a unos 1,20 en la panadería, y cuánto te falta para la siguiente. También `/barras` |
| `/emoji` | Cómo va tu cartera en las últimas 24 h, en una cara: de 💀 si baja más de un 10% a 🚀 si sube más de un 10%, pasando por 😐 si casi no se mueve. También `/cara` y `/animo` |
| `/tiempo` | Lo mismo que `/emoji`, pero como el parte del tiempo: de 🌪️ huracán si baja más de un 10% a 🌋 erupción si sube más de un 10%, pasando por ☁️ nublado si casi no se mueve. También `/clima` y `/parte` |
| `/carnet` | Cuántos carnets de conducir te da tu cartera, a unos 800 en autoescuela aprobando a la primera, y cuánto te falta para el siguiente. También `/carne` y `/autoescuela` |
| `/navidad` | Los días que faltan para Navidad y cuántas cestas navideñas te da tu cartera, a unos 100 cada una. También `/cesta` y `/xmas` |
| `/nochevieja` | Los días que faltan para Nochevieja, cuánto llevas de año y cuántas botellas de cava te da tu cartera, a unos 10 cada una. También `/findeaño` y `/uvas` |
| `/bigmac` | Cuántos Big Mac te da tu cartera, a unos 5,50 cada uno |
| `/gasolina` | Cuántos litros de gasolina te da tu cartera, a unos 1,80 el litro, y cuántos depósitos de 50 litros son |
| `/sueldo` | Cuántos meses (o años) de salario mínimo es tu cartera, con el SMI de 2026: 1.221 € en 14 pagas. Solo en euros |
| `/tendencias` | Las 7 criptos que más se buscan hoy en CoinGecko, con un botón en cada una para ver su precio y ponerle una alerta |
| `/tendencias avisa` | Te avisa cuando una de tu cartera o de las que vigilas entra en esa lista. Lo mira cada 6 horas (unas 120 consultas al mes) y de cada cripto avisa una vez a la semana como mucho. `/tendencias avisa no` lo quita |
| `/top` | Las 5 que más suben y las 5 que más bajan hoy de las 100 más grandes, con su precio |
| `/mapa` | Una imagen con las 30 más grandes en recuadros, cada uno del tamaño de lo que vale y en verde o en rojo según cuánto se ha movido en 24 h: cuanto más fuerte el color, más se ha movido. Las que vigilas o tienes en la cartera llevan borde. Arriba, lo que se ha movido el conjunto, pesando cada una por lo que vale. Sin estables ni copias de otra, como en `/altseason`. Gasta una consulta. También `/calor` |
| `/sectores` | Qué tipo de cripto sube hoy y cuál baja: memes, inteligencia artificial, DeFi, privacidad, videojuegos... 16 sectores con un par de ejemplos de cada uno, del que más sube al que más baja, y cuál tira del mercado. Cada sector va por lo que valen juntas todas sus criptos, según las categorías de CoinGecko. Gasta una consulta. También `/narrativas` |
| `/aleatoria` | Una de las 100 más grandes al azar, con su puesto, su precio y cómo va hoy. No saca las que ya vigilas ni las estables. Con un botón para pedir otra |
| `/caraocruz` | ¿Compro o vendo? Lo decide una moneda al aire (`/caraocruz btc`, con la cripto). Es de broma y no gasta consultas |
| `/dado` | Qué hacer con tu cripto según un dado: del 1 (vende todo) al 6 (compra más). También con la cripto, `/dado sol`. De broma, como `/caraocruz` |
| `/ppt piedra` | Piedra, papel o tijera contra el bot: si ganas, compra; si gana él, ni la toques; si empatáis, HODL. Vale `tijeras` y los emojis ✊ ✋ ✌️. También `/jugar` |
| `/adivina 70000` | Adivina a cuánto está Bitcoin, o la que digas (`/adivina eth 2500`), y te dice cuánto te has desviado, con nota: de 🎯 ¡Clavado! a 🧊 Ni de lejos. También `/adivinar` |
| `/frase` | Una frase famosa del mundo cripto al azar, de Satoshi, Hal Finney, Buffett y otros, con quién la dijo y cuándo. No gasta consultas |
| `/consejo` | Un consejo de inversión malísimo al azar, de broma, como el de comprar en máximos o apalancarse x100. No gasta consultas |
| `/excusa` | Una excusa al azar para cuando la cartera va mal, de broma, como que es culpa de la Fed o que los lunes no cuentan. No gasta consultas |
| `/refran` | Un refrán de toda la vida cambiado al mundo cripto, como «A quien madruga, el halving le ayuda». También `/refrán` y `/dicho`. No gasta consultas |
| `/horoscopo aries` | Tu horóscopo cripto de hoy, de broma, con la cripto y el número de la suerte. Vale con tilde (`/horóscopo géminis`) y en todo el día te dice lo mismo. No gasta consultas |
| `/galleta` | Tu galleta de la suerte, de broma, con una frase y seis números de la suerte. En todo el día te sale la misma. También `/fortuna`. No gasta consultas |
| `/tarot` | Sacas una carta del tarot cripto, de broma, como La Ballena o El Rug Pull, con lo que significa. También `/carta`. No gasta consultas |
| `/bola ¿vendo?` | La bola mágica contesta a lo que le preguntes, de broma: sí, no o que esperes al halving. También `/bola8`. No gasta consultas |
| `/chiste` | Un chiste de cripto al azar. No gasta consultas |
| `/dato` | Un dato curioso de cripto al azar, de las pizzas de 2010 al disco duro del vertedero. También `/curiosidad`. No gasta consultas |
| `/quiz` | Una pregunta de cultura cripto con tres respuestas en botones. Al pulsar te dice si has acertado y te ofrece otra. También `/trivial`. No gasta consultas |
| `/glosario fomo` | Lo que significa una palabra cripto: hodl, fomo, fud, dca, ath, ballena... A secas, la lista de las que sabe |
| `/miedo` | El índice de miedo y codicia del mercado (0 pánico, 100 euforia), con el de ayer y el de hace una semana. Viene de alternative.me y no gasta consultas de CoinGecko |
| `/sesgo` | Con qué humor del mercado compras y vendes: cuántas de tus compras y ventas fueron con miedo extremo, miedo, neutral, codicia o codicia extrema (el índice de alternative.me del día de cada una), y cómo van hoy las compras de cada grupo. Te dice si sueles comprar con codicia o vender con miedo, a partir de tres. Solo cuenta las de `/compra` y `/venta`, que llevan fecha. También `/humor` |
| `/comisionred` | Lo que cuesta ahora mover bitcoin, con prisa y sin ella, en dinero y en sat/vB, para un envío normal de una entrada y dos salidas. Te dice si está barata, normal o cara comparada con lo normal de la semana. Viene de mempool.space y no gasta consultas de CoinGecko. También `/mempool` |
| `/dificultad` | Cuándo toca el próximo ajuste de dificultad de bitcoin (cada 2.016 bloques, unas dos semanas), cuánto falta y cuánto se espera que suba o baje, con lo que cambió el anterior. Debajo, la potencia de minado (el hashrate) con una barrita de tres meses y cómo ha cambiado en 30 días: si cae un 10% o más, avisa de que muchos mineros están apagando máquinas. Viene de mempool.space y no gasta consultas de CoinGecko. También `/hashrate` y `/mineria` |
| `/hashribbons` | Las *hash ribbons* de bitcoin: la media de 30 días del hashrate contra la de 60. Cuando la primera cae por debajo, los mineros están capitulando (apagan máquinas y suelen vender), y el final de esa racha ha coincidido con los fondos de otros ciclos. Dice si están capitulando, si las medias se acaban de cruzar, si acaba de terminar (la señal de compra) o si el minado va sano, con una barrita del último año y las capitulaciones de los dos últimos años. Junta las rachas separadas por menos de una semana y no cuenta las de menos de siete días, que con datos diarios se cruzan cada dos por tres. Viene de mempool.space. También `/ribbons`, `/mineros` y `/capitulacion` |
| `/gwei` | Lo que cuesta ahora hacer algo en Ethereum: enviar ETH, enviar un token como USDT o USDC y un cambio en Uniswap, en tu moneda, con el gas en gwei según la prisa (sin prisa, normal o con prisa). Saca las propinas de los últimos 20 bloques de un nodo público (publicnode.com) y la base del próximo, que es lo que se quema sí o sí. Para pasarlo a dinero usa el último precio guardado de ethereum o, si no lo vigilas, gasta una consulta de CoinGecko. También `/gaseth` (`/gas` ya era el de la gasolina) |
| `/lightning` | Cómo está la red Lightning, la de pagos rápidos y baratos que va encima de bitcoin: cuánto bitcoin tiene dentro (en BTC y en dólares), cuántos nodos y canales, cómo ha cambiado todo en 30 días y lo nuevo de las últimas 24 h. Dice si crece o encoge (desde un 5% en el mes). Solo cuenta lo público. Viene de 1ml.com, porque mempool.space dejó de actualizarlo en agosto de 2026. No gasta consultas de CoinGecko. También `/ln` |
| `/comisionred 5` | Te avisa una vez cuando el envío de media hora baje a 5 sat/vB o menos, para pasar bitcoin a tu monedero cuando sale barato. Lo mira en cada consulta, en mempool.space. Si ya está así, te lo dice y no pone nada. `/comisionred no` lo quita |
| `/spread btc eth` | El precio de ahora en CoinGecko y en Binance, uno al lado del otro, y cuánto se separan (la que más, arriba). Con ⚠️ si pasa del 3%, que suele ser un dato malo: con esas el bot no te avisa hasta que cuadran. A secas, las que vigilas. Gasta una consulta. Solo en euros o dólares |
| `/funding btc` | Lo que pagan cada 8 horas en los futuros de Binance los que apuestan a que sube a los que apuestan a que baja, la media de la semana y un nivel: de "muchos apostando a que baja" a "muy apalancado al alza", que es cuando suelen venir las caídas bruscas. A secas, la primera que vigilo. No gasta consultas de CoinGecko. También `/financiacion` |
| `/funding btc avisa` | Te avisa cuando el funding de esa cripto se va a uno de los dos extremos: muy apalancado al alza (así suelen venir las caídas bruscas) o muchos apostando a que baja (a veces rebota de golpe). Mira la media de la semana, una vez por hora, y avisa al entrar en el extremo, no mientras sigue ahí. `/funding btc no` lo quita |
| `/oi btc` | Cuánto hay apostado en los futuros de Binance (el interés abierto) y cómo ha cambiado en 24 h, 7 y 30 días, con una barrita del mes. Lo cruza con el precio de la semana: si entra dinero mientras sube, si sube solo porque cierran los que apostaban a la baja, si se desinfla... Va en contratos y no en dólares, para que la subida del precio no parezca dinero nuevo. No gasta consultas de CoinGecko. También `/interesabierto` |
| `/longshort btc` | Cuántas cuentas de los futuros de Binance apuestan a que sube y cuántas a que baja, con una barrita del mes y su media, y lo mismo entre los que más mueven, contando por dinero. Lo compara con su propio mes, porque en bitcoin lo normal ya es un 65-75% a que sube: avisa si hoy hay más gente de lo normal a un lado, o si los pequeños y los grandes van cada uno por su lado. A secas, la primera que vigilo. No gasta consultas de CoinGecko. También `/largos` |
| `/longshort btc avisa` | Te avisa cuando en esa cripto se va más gente de lo normal a apostar a un lado: 5 puntos o más por encima o por debajo de la media de su mes. Lo mira cada cuatro horas (Binance lo da por días) y avisa al entrar, no mientras sigue ahí. `/longshort btc no` lo quita |
| `/profundidad btc` | Cuántos dólares habría que comprar o vender de golpe en Binance para mover el precio un 0,5%, un 1% y un 2%, hacia arriba y hacia abajo, sumando las órdenes que hay puestas. Dice si hay más esperando para comprar o para vender. Si el libro se acaba antes de llegar, lo marca con un + delante. Es una foto de ahora, solo de Binance al contado. A secas, la primera que vigilo. No gasta consultas de CoinGecko. También `/liquidez` |
| `/premium` | La prima de Coinbase: cuánto más (o menos) se paga por bitcoin en Coinbase que en Binance. Coinbase es donde compran los fondos y los grandes de EE. UU., así que si allí pagan más es que compran con ganas. Da la de ahora, una barrita de las dos últimas semanas con su media y entre qué cifras se ha movido. Al precio de Binance le quita lo que el USDT se separa del dólar, para que no parezca prima lo que no lo es. `/premium eth` lo saca de otra que esté en los dos. No gasta consultas de CoinGecko. También `/prima` |
| `/kimchi` | La prima kimchi: cuánto más (o menos) se paga por bitcoin en Corea, en Upbit, que en Binance. Corea pone trabas a sacar dinero del país, así que su precio puede separarse: si pagan mucho más, hay euforia (en los techos de 2018 y de 2021 pasó del 20%). Da la de hoy, una barrita del mes con su media y entre qué cifras se ha movido. Pasa los wones a dólares con el cambio del BCE (de frankfurter.dev, que no da fines de semana: esos días vale el del viernes), y no con el USDT de Upbit, que en Corea también va con prima. `/kimchi eth` lo saca de otra que esté en los dos. No gasta consultas de CoinGecko. También `/corea` |
| `/direccion bc1q... frío` | Vigila esa dirección de bitcoin con ese nombre y, mientras está en `--loop`, te avisa en cuanto entra o sale algo, sin esperar a que se confirme: cuánto, en BTC y en dinero, y con cuánto se queda. Sirve para tu monedero frío o para seguir a una ballena. Hasta 10. `/direccion` a secas, las que vigilo con lo que tiene cada una; `/direccion quitar frío`, deja de vigilarla. Las mira en mempool.space, así que ellos ven qué direcciones consultas. También `/monedero` |
| `/direccion 0x... ledger` | Lo mismo con una de ethereum (las que empiezan por `0x`). Avisa cuando cambia su saldo en ETH, ya confirmado, unos segundos después del bloque. Solo mira el ETH, no los tokens como USDT. La consulta va a un nodo público (publicnode.com), que ve qué direcciones miras, y el enlace a etherscan.io. Para que el aviso lleve su valor en dinero, vigila también ethereum o tenla en la cartera |
| `/buscar btc` | Encuentra el id de CoinGecko de una cripto |
| `/copia` | Las líneas `WATCHLIST`, `PORTFOLIO` y `RESUMEN_DIARIO` como están ahora, con lo cambiado por Telegram, listas para pegar en el `.env`. Para guardarlo por si cambias de servidor |
| `/ajustes` | Lo que tienes puesto en el `.env`: la moneda, cada cuánto consulta, los días que guarda, el resumen, el aviso de movimientos bruscos, el de máximos y mínimos y las horas tranquilas |
| `/consultas` | Cuántas consultas a CoinGecko llevas este mes |
| `/bot` | Si sigue funcionando: desde cuándo está encendido, cuándo fue el último ciclo y las consultas del mes. También con `/ping` |
| `/version` | Qué versión del bot está corriendo y, si lo bajaste con git, de qué día es el último cambio. También `/versión` |
| `/invitar` | Un código para que otra persona use tu bot con sus propias cosas: te lo da como `/start CÓDIGO` y esa persona se lo escribe al bot por privado. Vale una vez y caduca en 24 h. Hasta 10 invitados. Cada uno tiene sus avisos, su cartera, sus alertas y sus resúmenes, y no ve nada tuyo ni puede usar `/binance` ni `/consultas`. Los precios se piden una vez para todos, así que un invitado no gasta consultas de más (salvo las que pida él a mano). Lo de tu `.env` que no es la lista ni la cartera (la hora del resumen, los avisos bruscos...) vale para todos. `/dominancia` la ven con tu histórico, que es del mercado y no de nadie |
| `/usuarios` | A quién has invitado y desde cuándo, con un ✖ para quitarlo (`/expulsar`). Lo suyo no se borra, por si vuelve |
| `/mute` | Te pregunta cuánto tiempo callarse, con botones: 1 h, 4 h o hasta las 8:00 (si ya está callado, o tienes alguna cripto callada, te dice hasta cuándo) |
| `/mute 2h` | Calla los avisos ese rato, con un botón para deshacerlo |
| `/mute hasta 8:00` | Calla los avisos hasta esa hora (si ya ha pasado, la de mañana) |
| `/mute 7d salvo 10%` | Callado, pero si alguna de las que vigilas se mueve más de ese % en 24 h te escribe igual, como mucho una vez al día por cripto. Para irte de vacaciones sin perderte un desplome. Un `/mute` nuevo sin `salvo` lo quita |
| `/mute bitcoin 2h` | Calla solo esa cripto; las demás siguen avisando. Sus `/alerta` esperan a que vuelva |
| `/unmute` | Vuelve a avisar, también de las que callaste una a una, y te cuenta lo que te has perdido: cuánto se ha movido cada una que vigilas mientras callaba, entre qué precios, y tu cartera. Si el silencio se acaba solo, te llega lo mismo al acabarse |
| `/unmute bitcoin` | Vuelve a avisar solo de esa |
| `/ayuda` | Los comandos por temas (tu cartera, avisos, Hacienda…), con un botón para cada uno |
| `/ayuda avisos` | Los de un tema. `/ayuda todo` saca la lista entera de golpe |
| `/ayuda alerta` | Ese comando con ejemplos de todo lo que admite |

En los comandos vale el símbolo de las más conocidas en vez del id: `/precio btc`,
`/alerta eth 3000`, `/compra sol 2`. Para las demás, el id de `/buscar`.

Al escribir `/` en el chat te salen solos. Solo contesta a tu chat id, y si
estaba apagado, al volver ignora lo que le escribiste hace más de 10 minutos.

**Botones en los avisos:**

Cada aviso lleva debajo unos botones para reaccionar de un toque:

- **📈 Gráfica**: la de las últimas 24 h, como `/historico`.
- **🎯 Si vuelve a 64.000**: te avisa una vez si vuelve al precio que acaba de
  cruzar, como `/alerta`.
- **🔁 Otra a +5%**: solo cuando salta una `/alerta`. Te pone otra un 5 % más
  allá del precio de ahora, hacia donde iba (si bajaba, `-5%`).
- **🔕 Callar 1 h**: como `/mute 1h`.

Si en un mensaje vienen varias criptos, salen los botones de las tres primeras.

`/mute` a secas te deja elegir cuánto con un toque, y al callarlo sale un
**🔔 Volver a avisar** por si te arrepientes.

`/precio` de una sola lleva **🔔 Si sube un 5%** y **🔔 Si baja un 5%**, que
te ponen esa `/alerta` desde lo que vale ahora, y un **📈 Gráfica** con la de
las últimas 24 h si tiene precios guardados.

`/status`, `/resumen`, `/cartera`, `/alertas` y `/precio` de varias llevan un
**🔄 Actualizar** para volver a pedirlos de un toque.

**Alertas de una sola vez:**

Escríbele `/alerta bitcoin 70000` y te avisa cuando llegue a 70.000, suba o
baje, según dónde esté ahora. Avisa una vez y se borra sola, sin tocar el `.env`
ni reiniciar. Vale cualquier cripto, aunque no esté en `WATCHLIST`, y puedes
escribir el precio como `70.000` o `0,35`. Si estás en `/mute`, no se pierde: te
avisa al volver si sigue en ese precio.

Si no quieres hacer cuentas, ponlo en porcentaje: `/alerta bitcoin +10%` o
`/alerta solana -5%`. Calcula el precio con lo que vale en ese momento y te
contesta a cuánto ha quedado. El signo es obligatorio, que un `10%` a secas no
dice si esperar a que suba o a que baje.

Para que no se te acumulen alertas viejas, ponles caducidad al final:
`/alerta bitcoin 70000 7d` o `/alerta solana +10% 12h`. Si en ese tiempo no
llega, se borra sola y te manda un ⌛ sin sonido para que lo sepas. `/alertas`
te enseña cuándo caduca cada una. Las que pongas sin tramo no caducan nunca.

Lo que escribas después del precio (o del tramo) se guarda como nota y te sale
con el aviso: `/alerta bitcoin 70000 vender la mitad`. Así te acuerdas de por
qué la pusiste.

El resumen del día (y `/resumen`) te enseña las que están a menos de un 3 % de
saltar. Si no hay ninguna tan cerca, te dice cuántas tienes y cuál está más
cerca, para que no se te olviden.

Con `cartera` en vez de una cripto, mira lo que vale todo lo que tienes junto:
`/alerta cartera 5000` o `/alerta cartera -10%`. Si en un ciclo falta el precio
de alguna, ese ciclo no la mira, que el total saldría más bajo de lo que es y
daría un aviso falso.

**Cambiar lo que vigila sin tocar el `.env`:**

`/vigilar` admite lo mismo que `WATCHLIST`, con espacios en vez de dos puntos:
`/vigilar solana 10`, `/vigilar solana %5` o `/vigilar bitcoin 55000 75000`
(con un `-` dejas un lado sin vigilar: `/vigilar ethereum - 4000`). Se aplica al
momento, sin reiniciar, y se guarda aunque se apague.

El `.env` sigue siendo la base y lo que hagas por Telegram va encima. Si una
cripto la has tocado por Telegram, manda eso aunque luego cambies el `.env`.
`/vigilar` te lo marca con *(desde Telegram)*.

**Ver cómo van ahora mismo:**
```
python main.py --status
```
Te manda a Telegram un resumen con el precio de todo lo que vigilas y cuánto ha
cambiado en las últimas 24 horas. Ese dato lo da CoinGecko en la misma consulta,
así que sale desde el primer momento aunque acabes de instalarlo.

Debajo de cada una te dice a qué precio saltaría el siguiente aviso y cuánto le
falta, por ejemplo `↑ €64.000,00 (+1.59%) · ↓ €63.000,00 (-0.90%)`. Así sabes si
está a punto de avisarte o le queda mucho.

**Ver cuánto vale lo que tienes:**
```
PORTFOLIO=bitcoin:0.016:1000,ethereum:0.4:1000
```
Cada una es `cripto:cantidad:lo que te costó`. La cantidad es la que te sale en
el exchange; lo que te costó es opcional, pero sin eso no sabe si ganas o
pierdes. El resumen (`--status`, `/status` y el diario) añade al final lo que
vale cada una, cuánto llevas ganado o perdido con ella y el total. Debajo de
cada una te pone qué parte del total es, a cuánto te salió de media y a cuánto
está ahora (`38% del total · te salió a €62.500,00 · ahora €76.258,00`). Si solo
quieres eso, escríbele `/cartera`.

`/cartera` además te manda una gráfica de lo que ha valido, con una línea
discontinua en lo que invertiste. Ojo: usa las cantidades de ahora, así que es
lo que habría valido lo que tienes hoy, no tu historial de compras. Empieza a
tener datos en cuanto el bot lleva un rato en `--loop`.

**Sacar los precios a una hoja de cálculo:**

`/exportar bitcoin 30d` te manda por Telegram un archivo `.csv` con todos los
precios guardados de ese tramo, con la fecha en tu hora. Va con punto y coma y
coma decimal, que es como lo abre bien Excel en español con doble clic. Solo
tiene lo que el bot ha ido guardando, así que no llega más atrás de
`HISTORY_DAYS` ni de cuando lo instalaste.

`/exportar movimientos` hace lo mismo con todo lo apuntado con `/compra` y
`/venta`: fecha, cantidad, importe, precio por unidad, ganancia de cada venta y
nota. Lo del `PORTFOLIO` del `.env` no sale, porque no tiene fecha.

**Saber cuánto tendrías si hubieras comprado:**

`/si 1000 bitcoin 30d` te dice cuánto valdrían hoy 1.000 € metidos en Bitcoin
hace 30 días, y cuánto habrías ganado o perdido. Sale de los precios que ya
tiene guardados, así que no gasta consultas, pero solo vale con las criptos que
vigila y no llega más atrás de cuando lo instalaste.

**Saber cuánto valdría tu cartera a un precio:**

`/objetivo bitcoin 100000` te dice cuánto valdría todo lo que tienes si Bitcoin
llegara a 100.000 €, cuánto es respecto a hoy y, si apuntaste lo que pagaste,
cuánto ganarías. Las demás criptos las deja a su precio de ahora. Solo vale con
las que tienes en la cartera.

**Apuntar compras y ventas desde el móvil:**

No hace falta tocar el `.env` cada vez que compras. Escríbele
`/compra bitcoin 0.01 600` y suma 0,01 a lo que tienes y 600 € a lo que te
costó. Si no pones el precio (`/compra solana 3`), lo apunta a lo que vale en
ese momento. Si prefieres poner a cuánto te salió cada una, como lo enseña el
exchange, va con `@`: `/compra bitcoin 0.01 @60000`.

`/venta bitcoin 0.005 350` lo resta, y lo que te costó baja en la misma
proporción: si vendes la mitad, se va la mitad de lo invertido. El último número
es lo que te dieron, o con `@` a cuánto cada una; sin él, se apunta al precio de
ahora. `/venta bitcoin todo` la saca de la cartera.

`/ganancias` suma lo que has sacado con cada venta, contando lo que te costó
esa parte al precio medio. Las ventas apuntadas antes de esto no guardaban el
precio, así que no entran.

Si te equivocas, cada respuesta lleva un **↩️ Deshacer** que la deja como
estaba. `/movimientos` te enseña las últimas que has apuntado, y `/deshacer`
quita la última (repítelo para ir más atrás).

Como con `/vigilar`, el `.env` es la base y lo de Telegram va encima. Si una
cripto la cambias por Telegram, deja de mirar lo que ponga de ella `PORTFOLIO`.

**Callar los avisos un rato:**
```
python main.py --mute 2h
```
No te avisa durante dos horas. Vale `30m`, `2h` o `1d`; sin letra se entienden
horas. También hasta una hora: `--mute "hasta 8:00"` (si ya ha pasado, la de
mañana). Sigue mirando y guardando precios, solo se calla.

Para volver antes de tiempo:
```
python main.py --unmute
```

El silencio se guarda, así que aguanta aunque reinicies o se apague el servidor.
Y `--status` te sigue funcionando: lo que se calla son los avisos automáticos, no
lo que pidas tú.

**Enterarte de los desplomes:**

```
MOVIMIENTO_BRUSCO=8%/1h
```
Te avisa si cualquiera de tus criptos sube o baja un 8% en menos de una hora,
aunque no cruce ninguno de sus niveles. Cuenta desde el punto más alto o más
bajo de esa hora, así que también pilla un "sube un 10% y lo devuelve todo".
Tras un aviso, solo vuelve a avisar si se mueve otro 8% desde ahí.

**Saber cuándo marca un máximo o un mínimo:**

```
MAXIMOS_MINIMOS=30d
```
Te avisa cuando una de tus criptos supera el precio más alto de los últimos 30
días, o baja del más bajo. Lo mira con los precios que ya tiene guardados, así
que no gasta consultas, pero necesita llevar esos 30 días funcionando: hasta
entonces no dice nada, para no llamar "máximo de 30 días" a algo de anteayer.
Avisa como mucho una vez al día de cada cosa, que en plena subida cada ciclo es
un máximo nuevo. Tiene que ser de 2 días o más, y no más de los que guarda
`HISTORY_DAYS`.

**Enterarte si tu cartera se hunde:**

```
CAIDA_CARTERA=20%
```
Si tienes `PORTFOLIO`, te avisa cuando tu cartera vale un 20% menos que su
récord, el mismo de `/record`. Si sigue bajando, vuelve a avisar al 40%, al
60%... pero no en cada ciclo. Cuando marca un récord nuevo, empieza de cero.
Con `/mute cartera 1d` lo callas; si al volver sigue igual de abajo, te llega.

**Enterarte si una sola cripto se come la cartera:**

```
CONCENTRACION=70%
```
Si tienes `PORTFOLIO` y una cripto pasa a ser el 70% de lo que vale, te avisa
una vez, con lo que caería la cartera si esa cae un 20%. No repite mientras
siga por ahí; si baja del 65% y vuelve a pasar, sí. También se calla con
`/mute cartera`.

**Enterarte si una cripto se pasa de subidas o de bajadas:**

```
AVISO_RSI=si
```
Te avisa una vez cuando una que vigilas entra en sobrecompra (RSI de 70 o más)
o en sobreventa (30 o menos), sin tener que preguntar con `/rsi`. No repite
mientras siga por ahí; para volver a avisar tiene que bajar de 65 o subir de 35.
Necesita 15 días seguidos guardados de esa cripto y se calla con
`/mute bitcoin`.

**Enterarte de una cruz dorada o de la muerte:**

```
AVISO_CRUCE=si
HISTORY_DAYS=366
```
Te avisa cuando la media de 50 días de una que vigilas pasa por encima de la de
200 (🌟 cruz dorada) o por debajo (☠️ cruz de la muerte). Para que no salte y
vuelva a saltar el mismo día cuando van casi iguales, tienen que separarse un
0,5 %. La primera vez que mira solo apunta dónde está, que eso no es un cruce.
Necesita 200 días guardados: con `HISTORY_DAYS` más corto no arranca, y con
`/rellenar btc` no tienes que esperar. Se calla con `/mute bitcoin`.

**Enterarte cuando una cripto se mueve más de lo normal:**

```
AVISO_VOLUMEN=si
```
Te avisa una vez cuando lo negociado en 24 h de una que vigilas pasa del triple
de lo normal (la mediana de sus últimos 30 días), que suele ser que hay noticia
detrás. No repite hasta que baje del doble. El volumen viene en la misma
consulta que el precio, así que no gasta más. Necesita una semana guardando
volumen: `/rellenar` no lo baja. Se calla con `/mute bitcoin`.

**Enterarte cuando una cripto se queda demasiado quieta:**

```
AVISO_CALMA=si
```
Te avisa una vez cuando una que vigilas lleva 7 días moviéndose mucho menos de lo
normal: una de las semanas más tranquilas (el 10 % de abajo) de lo que tiene
guardado. Se dice que va antes de un movimiento fuerte, aunque no hacia dónde y
no siempre se cumple: por eso te cuenta cuánto se movió la semana siguiente las
otras veces. No repite hasta
que vuelva a moverse. Necesita 38 días guardados: con `/rellenar btc` no tienes
que esperar. Se calla con `/mute bitcoin`.

**Enterarte si una estable se sale de su dólar:**

No hay que poner nada. Si tienes o vigilas USDT, USDC o DAI (`tether`,
`usd-coin` o `dai`) y se aleja más de un 1 % de su dólar, te avisa una vez, y
otra cuando vuelva a menos del 0,5 %. El precio en dólares viene en la misma
consulta de siempre, así que no gasta consultas aunque tu moneda sea el euro.
Se calla con `/mute tether`.

**Que no se pierda nada si se muere el servidor:**

```
COPIA_SEMANAL=si
```
Te manda cada 7 días, sin sonar, un zip con la base de datos. Con `/backup` la
pides cuando quieras. Ojo: lleva todas tus compras y ventas y se queda en el chat.

Para recuperarla: para el bot, descomprime el zip y pon el `prices.db` en `data/`
(o donde diga `DATABASE_PATH`). Lo del `.env` no va en la copia; para eso está
`/copia`.

**Recibir un resumen cada mañana:**

Pon la hora en el `.env`:
```
RESUMEN_DIARIO=09:00
```
Mientras esté en modo `--loop`, te manda cada día a esa hora lo mismo que
`--status`. Si a esa hora estaba apagado, te lo manda al volver, pero solo hasta
dos horas tarde. Con `--mute` tampoco llega.

Si alguna compra apuntada por Telegram cumple años ese día, te la recuerda con
lo que vale hoy: `🎂 Hace 1 año compraste 0,01 de Bitcoin por €600,00: hoy vale
€1.100,00 🔺 +83.33%`. Las del 29 de febrero, el 28 los años que no son
bisiestos.

Desde Telegram puedes cambiar la hora con `/horario 8:30` o quitarlo con
`/horario no`, sin tocar el `.env`. Lo que pongas ahí manda sobre el `.env`.

Si además tienes `PORTFOLIO`, los domingos a esa misma hora te llega **tu
semana**: cuánto ha ganado o perdido la cartera en 7 días, cada cripto de la que
mejor ha ido a la que peor y la gráfica de la semana. Sale de los precios que ya
tiene guardados, así que no gasta consultas, pero necesita que el bot lleve
unos días en `--loop`. Con `/semana` lo pides cuando quieras.

Y el día 1 de cada mes, también a esa hora, te llega **tu mes**: lo mismo, pero
del mes que acaba de terminar, del día 1 al último. Con `/mes` ves el que va en
curso. Si `HISTORY_DAYS` es menor de 31, saldrá solo el trozo que tenga.

Y el 1 de enero, **tu año**: cuánto ha ido la cartera, la cripto que mejor y la
que peor, el mejor y el peor mes, cuántas compras y ventas hiciste, lo ganado
vendiendo y tu mejor y tu peor compra, mirada a 31 de diciembre. Con
`/anual 2025` lo ves de cualquier año, también el que va en curso. Para que la
cartera salga del año entero, `HISTORY_DAYS=366`.

Y entre el 15 y el 28 de diciembre, una sola vez, **lo que te ahorrarías en
Hacienda**: si llevas ganancia vendiendo este año y algo de tu cartera va en
pérdidas, lo mismo que `/compensar`, a tiempo de venderlo antes del 1 de enero.
Si no hay nada que ahorrar, no te llega nada.

Y entre el 1 y el 15 de abril, cuando abre la campaña, **la Renta**: si el año
pasado vendiste algo o cobraste staking, lo mismo que `/impuestos` de ese año,
con dos botones para sacar el informe en PDF y el CSV venta a venta. Las
pérdidas también salen, que si no las declaras no las puedes restar luego.

**Que no te despierte:**
```
HORAS_TRANQUILAS=23-8
```
De 11 de la noche a 8 de la mañana los avisos llegan sin sonar ni vibrar. No
se pierde ninguno: por la mañana los tienes todos. Lo que le preguntes por
Telegram sí suena, que si escribes es que estás despierto.

Desde Telegram lo cambias con `/dormir 0-7` o lo quitas con `/dormir no`, y
manda sobre el `.env`.

**Ver el histórico de una cripto:**
```
python main.py --history bitcoin
```
Lista los últimos precios guardados y, debajo, un gráfico de una línea con la
forma que ha tenido, más el máximo, el mínimo, la media y cuánto ha variado.

---

El panel web (`--panel`), el widget del móvil, `/panel` y `/enlace` van en
[el panel](panel.md).
