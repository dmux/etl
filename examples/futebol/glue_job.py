"""Script do job AWS Glue `futebol-pipeline` (Command.ScriptLocation). Só chama o pacote.

O pacote `etl_futebol` chega pelo `--extra-py-files` (ADR-009). Argumentos esperados:
`--camadas bronze,silver,gold,verificacao --fonte s3a://.../fonte --warehouse s3a://.../warehouse`.
"""

import sys

from etl_futebol.cli.glue import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
