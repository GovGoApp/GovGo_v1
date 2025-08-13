#!/usr/bin/env python3
print("TESTE SIMPLES FUNCIONANDO!")

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--test', action='store_true')
args = parser.parse_args()

if args.test:
    print("MODO TESTE DETECTADO!")
else:
    print("MODO NORMAL")

print("SCRIPT CONCLUÍDO")
