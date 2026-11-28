"""Los avisos sueltos de un ciclo, juntos en un mensaje en vez de uno tras otro."""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Buzon:
    textos: list[str] = field(default_factory=list)
    al_llegar: list[Callable[[], None]] = field(default_factory=list)

    def echar(self, texto: str, al_llegar: Callable[[], None] | None = None) -> None:
        """Deja un aviso. al_llegar se ejecuta solo si el mensaje llega."""
        self.textos.append(texto)
        if al_llegar is not None:
            self.al_llegar.append(al_llegar)

    def vacio(self) -> bool:
        return not self.textos

    def juntar(self) -> str:
        if len(self.textos) == 1:
            return self.textos[0]
        return f"<b>{len(self.textos)} avisos</b>\n\n" + "\n\n".join(self.textos)

    def llegaron(self) -> None:
        # Se vacía antes: si uno revienta a medias, no se apunta dos veces.
        pendientes, self.al_llegar = self.al_llegar, []
        self.textos = []
        for hecho in pendientes:
            hecho()

    def entregar(self, mandar: Callable[[str], bool]) -> bool:
        """Lo manda todo junto. Si no llega, no se apunta nada y vuelve a saltar."""
        if self.vacio():
            return True
        if not mandar(self.juntar()):
            return False
        self.llegaron()
        return True
