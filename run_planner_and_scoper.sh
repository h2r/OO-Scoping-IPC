#!/bin/bash

python3 parse_and_scope_pddl.py
enhsp -o examples/multi_monkeys_playroom/multi_monkeys_playroom.pddl -f examples/multi_monkeys_playroom/prob-01_scoped.pddl