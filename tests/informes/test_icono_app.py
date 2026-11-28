import io

from PIL import Image

from crypto_tracker.informes import icono_app


def test_png_del_tamano_pedido_y_sin_transparencia():
    imagen = Image.open(io.BytesIO(icono_app.png(192)))

    assert imagen.size == (192, 192)
    # iOS pinta de negro lo transparente: el color tiene que llegar al borde.
    assert imagen.mode == "RGB"
    assert imagen.getpixel((0, 0)) == (0x6D, 0x4A, 0xFF)
