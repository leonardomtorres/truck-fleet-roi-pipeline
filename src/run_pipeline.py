"""Roda as 3 camadas em sequencia: bronze -> silver -> gold."""

import bronze
import silver
import gold


def main():
    for nome, modulo in [("bronze", bronze), ("silver", silver), ("gold", gold)]:
        print(f"\n=== camada {nome} ===")
        modulo.main()


if __name__ == "__main__":
    main()
