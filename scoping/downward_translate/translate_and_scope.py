#! /usr/bin/env python3


import os
import sys
import traceback
from typing import Iterable


def python_version_supported():
    return sys.version_info >= (3, 6)


if not python_version_supported():
    sys.exit("Error: Translator only supports Python >= 3.6.")


from collections import defaultdict
from copy import deepcopy
from itertools import product

import signal


from oo_scoping.downward_translate import axiom_rules
from oo_scoping.downward_translate import fact_groups
from oo_scoping.downward_translate import instantiate
from oo_scoping.downward_translate import normalize
from oo_scoping.downward_translate import options
from oo_scoping.downward_translate import pddl
from oo_scoping.downward_translate import pddl_parser
from oo_scoping.downward_translate import sas_tasks
from oo_scoping import sas_parser

from oo_scoping.downward_translate import simplify
from oo_scoping.downward_translate import timers
from oo_scoping.downward_translate import tools
from oo_scoping.downward_translate import variable_order

from oo_scoping.downward_translate import scoping_sas_converter
from oo_scoping.scoping import scope
from oo_scoping.writeback_sas import writeback_scoped_sas
from oo_scoping.utils import get_atoms
from oo_scoping.skill_classes import SkillPDDL
from oo_scoping.paths import (
    get_effectively_relevant_fluents_file_path,
    get_scoped_file_path,
)

# Profile imports
# import cProfile
# import pstats
# from pstats import SortKey

# TODO: The translator may generate trivial derived variables which are always
# true, for example if there ia a derived predicate in the input that only
# depends on (non-derived) variables which are detected as always true.
# Such a situation was encountered in the PSR-STRIPS-DerivedPredicates domain.
# Such "always-true" variables should best be compiled away, but it is
# not clear what the best place to do this should be. Similar
# simplifications might be possible elsewhere, for example if a
# derived variable is synonymous with another variable (derived or
# non-derived).

DEBUG = False


## For a full list of exit codes, please see driver/returncodes.py. Here,
## we only list codes that are used by the translator component of the planner.
TRANSLATE_OUT_OF_MEMORY = 20
TRANSLATE_OUT_OF_TIME = 21

simplified_effect_condition_counter = 0
added_implied_precondition_counter = 0


def strips_to_sas_dictionary(groups, assert_partial):
    dictionary = {}
    for var_no, group in enumerate(groups):
        for val_no, atom in enumerate(group):
            dictionary.setdefault(atom, []).append((var_no, val_no))
    if assert_partial:
        assert all(len(sas_pairs) == 1 for sas_pairs in dictionary.values())
    return [len(group) + 1 for group in groups], dictionary


def translate_strips_conditions_aux(conditions, dictionary, ranges):
    condition = {}
    for fact in conditions:
        if fact.negated:
            # we handle negative conditions later, because then we
            # can recognize when the negative condition is already
            # ensured by a positive condition
            continue
        for var, val in dictionary.get(fact, ()):
            # The default () here is a bit of a hack. For goals (but
            # only for goals!), we can get static facts here. They
            # cannot be statically false (that would have been
            # detected earlier), and hence they are statically true
            # and don't need to be translated.
            # TODO: This would not be necessary if we dealt with goals
            # in the same way we deal with operator preconditions etc.,
            # where static facts disappear during grounding. So change
            # this when the goal code is refactored (also below). (**)
            if condition.get(var) is not None and val not in condition.get(var):
                # Conflicting conditions on this variable: Operator invalid.
                return None
            condition[var] = {val}

    def number_of_values(var_vals_pair):
        var, vals = var_vals_pair
        return len(vals)

    for fact in conditions:
        if fact.negated:
            ## Note: here we use a different solution than in Sec. 10.6.4
            ## of the thesis. Compare the last sentences of the third
            ## paragraph of the section.
            ## We could do what is written there. As a test case,
            ## consider Airport ADL tasks with only one airport, where
            ## (occupied ?x) variables are encoded in a single variable,
            ## and conditions like (not (occupied ?x)) do occur in
            ## preconditions.
            ## However, here we avoid introducing new derived predicates
            ## by treat the negative precondition as a disjunctive
            ## precondition and expanding it by "multiplying out" the
            ## possibilities.  This can lead to an exponential blow-up so
            ## it would be nice to choose the behaviour as an option.
            done = False
            new_condition = {}
            atom = pddl.Atom(fact.predicate, fact.args)  # force positive
            for var, val in dictionary.get(atom, ()):
                # see comment (**) above
                poss_vals = set(range(ranges[var]))
                poss_vals.remove(val)

                if condition.get(var) is None:
                    assert new_condition.get(var) is None
                    new_condition[var] = poss_vals
                else:
                    # constrain existing condition on var
                    prev_possible_vals = condition.get(var)
                    done = True
                    prev_possible_vals.intersection_update(poss_vals)
                    if len(prev_possible_vals) == 0:
                        # Conflicting conditions on this variable:
                        # Operator invalid.
                        return None

            if not done and len(new_condition) != 0:
                # we did not enforce the negative condition by constraining
                # an existing condition on one of the variables representing
                # this atom. So we need to introduce a new condition:
                # We can select any from new_condition and currently prefer the
                # smallest one.
                candidates = sorted(new_condition.items(), key=number_of_values)
                var, vals = candidates[0]
                condition[var] = vals

        def multiply_out(condition):  # destroys the input
            sorted_conds = sorted(condition.items(), key=number_of_values)
            flat_conds = [{}]
            for var, vals in sorted_conds:
                if len(vals) == 1:
                    for cond in flat_conds:
                        cond[var] = vals.pop()  # destroys the input here
                else:
                    new_conds = []
                    for cond in flat_conds:
                        for val in vals:
                            new_cond = deepcopy(cond)
                            new_cond[var] = val
                            new_conds.append(new_cond)
                    flat_conds = new_conds
            return flat_conds

    return multiply_out(condition)


def translate_strips_conditions(
    conditions, dictionary, ranges, mutex_dict, mutex_ranges
):
    if not conditions:
        return [{}]  # Quick exit for common case.

    # Check if the condition violates any mutexes.
    if translate_strips_conditions_aux(conditions, mutex_dict, mutex_ranges) is None:
        return None

    return translate_strips_conditions_aux(conditions, dictionary, ranges)


def translate_strips_operator(
    operator, dictionary, ranges, mutex_dict, mutex_ranges, implied_facts
):
    conditions = translate_strips_conditions(
        operator.precondition, dictionary, ranges, mutex_dict, mutex_ranges
    )
    if conditions is None:
        return []
    sas_operators = []
    for condition in conditions:
        op = translate_strips_operator_aux(
            operator,
            dictionary,
            ranges,
            mutex_dict,
            mutex_ranges,
            implied_facts,
            condition,
        )
        if op is not None:
            sas_operators.append(op)
    return sas_operators


def negate_and_translate_condition(
    condition, dictionary, ranges, mutex_dict, mutex_ranges
):
    # condition is a list of lists of literals (DNF)
    # the result is the negation of the condition in DNF in
    # finite-domain representation (a list of dictionaries that map
    # variables to values)
    negation = []
    if [] in condition:  # condition always satisfied
        return None  # negation unsatisfiable
    for combination in product(*condition):
        cond = [l.negate() for l in combination]
        cond = translate_strips_conditions(
            cond, dictionary, ranges, mutex_dict, mutex_ranges
        )
        if cond is not None:
            negation.extend(cond)
    return negation if negation else None


def translate_strips_operator_aux(
    operator, dictionary, ranges, mutex_dict, mutex_ranges, implied_facts, condition
):

    # collect all add effects
    effects_by_variable = defaultdict(lambda: defaultdict(list))
    # effects_by_variables: var -> val -> list(FDR conditions)
    add_conds_by_variable = defaultdict(list)
    for conditions, fact in operator.add_effects:
        eff_condition_list = translate_strips_conditions(
            conditions, dictionary, ranges, mutex_dict, mutex_ranges
        )
        if eff_condition_list is None:  # Impossible condition for this effect.
            continue
        for var, val in dictionary[fact]:
            effects_by_variable[var][val].extend(eff_condition_list)
            add_conds_by_variable[var].append(conditions)

    # collect all del effects
    del_effects_by_variable = defaultdict(lambda: defaultdict(list))
    for conditions, fact in operator.del_effects:
        eff_condition_list = translate_strips_conditions(
            conditions, dictionary, ranges, mutex_dict, mutex_ranges
        )
        if eff_condition_list is None:  # Impossible condition for this effect.
            continue
        for var, val in dictionary[fact]:
            del_effects_by_variable[var][val].extend(eff_condition_list)

    # add effect var=none_of_those for all del effects with the additional
    # condition that the deleted value has been true and no add effect triggers
    for var in del_effects_by_variable:
        no_add_effect_condition = negate_and_translate_condition(
            add_conds_by_variable[var], dictionary, ranges, mutex_dict, mutex_ranges
        )
        if no_add_effect_condition is None:  # there is always an add effect
            continue
        none_of_those = ranges[var] - 1
        for val, conds in del_effects_by_variable[var].items():
            for cond in conds:
                # add guard
                if var in cond and cond[var] != val:
                    continue  # condition inconsistent with deleted atom
                cond[var] = val
                # add condition that no add effect triggers
                for no_add_cond in no_add_effect_condition:
                    new_cond = dict(cond)
                    # This is a rather expensive step. We try every no_add_cond
                    # with every condition of the delete effect and discard the
                    # overal combination if it is unsatisfiable. Since
                    # no_add_effect_condition is precomputed it can contain many
                    # no_add_conds in which a certain literal occurs. So if cond
                    # plus the literal is already unsatisfiable, we still try
                    # all these combinations. A possible optimization would be
                    # to re-compute no_add_effect_condition for every delete
                    # effect and to unfold the product(*condition) in
                    # negate_and_translate_condition to allow an early break.
                    for cvar, cval in no_add_cond.items():
                        if cvar in new_cond and new_cond[cvar] != cval:
                            # the del effect condition plus the deleted atom
                            # imply that some add effect on the variable
                            # triggers
                            break
                        new_cond[cvar] = cval
                    else:
                        effects_by_variable[var][none_of_those].append(new_cond)

    return build_sas_operator(
        operator.name,
        condition,
        effects_by_variable,
        operator.cost,
        ranges,
        implied_facts,
    )


def build_sas_operator(
    name, condition, effects_by_variable, cost, ranges, implied_facts
):
    if options.add_implied_preconditions:
        implied_precondition = set()
        for fact in condition.items():
            implied_precondition.update(implied_facts[fact])
    prevail_and_pre = dict(condition)
    pre_post = []
    for var, effects_on_var in effects_by_variable.items():
        orig_pre = condition.get(var, -1)
        added_effect = False
        for post, eff_conditions in effects_on_var.items():
            pre = orig_pre
            # if the effect does not change the variable value, we ignore it
            if pre == post:
                continue
            eff_condition_lists = [
                sorted(eff_cond.items()) for eff_cond in eff_conditions
            ]
            if ranges[var] == 2:
                # Apply simplifications for binary variables.
                if prune_stupid_effect_conditions(
                    var, post, eff_condition_lists, effects_on_var
                ):
                    global simplified_effect_condition_counter
                    simplified_effect_condition_counter += 1
                if (
                    options.add_implied_preconditions
                    and pre == -1
                    and (var, 1 - post) in implied_precondition
                ):
                    global added_implied_precondition_counter
                    added_implied_precondition_counter += 1
                    pre = 1 - post
            for eff_condition in eff_condition_lists:
                # we do not need to represent a precondition as effect condition
                # and we do not want to keep an effect whose condition contradicts
                # a pre- or prevail condition
                filtered_eff_condition = []
                eff_condition_contradicts_precondition = False
                for variable, value in eff_condition:
                    if variable in prevail_and_pre:
                        if prevail_and_pre[variable] != value:
                            eff_condition_contradicts_precondition = True
                            break
                    else:
                        filtered_eff_condition.append((variable, value))
                if eff_condition_contradicts_precondition:
                    continue
                pre_post.append((var, pre, post, filtered_eff_condition))
                added_effect = True
        if added_effect:
            # the condition on var is not a prevail condition but a
            # precondition, so we remove it from the prevail condition
            condition.pop(var, -1)
    if not pre_post:  # operator is noop
        return None
    prevail = list(condition.items())
    return sas_tasks.SASOperator(name, prevail, pre_post, cost)


def prune_stupid_effect_conditions(var, val, conditions, effects_on_var):
    ## (IF <conditions> THEN <var> := <val>) is a conditional effect.
    ## <var> is guaranteed to be a binary variable.
    ## <conditions> is in DNF representation (list of lists).
    ##
    ## We simplify <conditions> by applying two rules:
    ## 1. Conditions of the form "var = dualval" where var is the
    ##    effect variable and dualval != val can be omitted.
    ##    (If var != dualval, then var == val because it is binary,
    ##    which means that in such situations the effect is a no-op.)
    ##    The condition can only be omitted if there is no effect
    ##    producing dualval (see issue736).
    ## 2. If conditions contains any empty list, it is equivalent
    ##    to True and we can remove all other disjuncts.
    ##
    ## returns True when anything was changed
    if conditions == [[]]:
        return False  # Quick exit for common case.
    assert val in [0, 1]
    dual_val = 1 - val
    dual_fact = (var, dual_val)
    if dual_val in effects_on_var:
        return False
    simplified = False
    for condition in conditions:
        # Apply rule 1.
        while dual_fact in condition:
            # print "*** Removing dual condition"
            simplified = True
            condition.remove(dual_fact)
        # Apply rule 2.
        if not condition:
            conditions[:] = [[]]
            simplified = True
            break
    return simplified


def translate_strips_axiom(axiom, dictionary, ranges, mutex_dict, mutex_ranges):
    conditions = translate_strips_conditions(
        axiom.condition, dictionary, ranges, mutex_dict, mutex_ranges
    )
    if conditions is None:
        return []
    if axiom.effect.negated:
        [(var, _)] = dictionary[axiom.effect.positive()]
        effect = (var, ranges[var] - 1)
    else:
        [effect] = dictionary[axiom.effect]
    axioms = []
    for condition in conditions:
        axioms.append(sas_tasks.SASAxiom(condition.items(), effect))
    return axioms


def translate_strips_operators(
    actions, strips_to_sas, ranges, mutex_dict, mutex_ranges, implied_facts
):
    result = []
    for action in actions:
        sas_ops = translate_strips_operator(
            action, strips_to_sas, ranges, mutex_dict, mutex_ranges, implied_facts
        )
        result.extend(sas_ops)
    return result


def translate_strips_axioms(axioms, strips_to_sas, ranges, mutex_dict, mutex_ranges):
    result = []
    for axiom in axioms:
        sas_axioms = translate_strips_axiom(
            axiom, strips_to_sas, ranges, mutex_dict, mutex_ranges
        )
        result.extend(sas_axioms)
    return result


def dump_task(init, goals, actions, axioms, axiom_layer_dict):
    old_stdout = sys.stdout
    with open("output.dump", "w") as dump_file:
        sys.stdout = dump_file
        print("Initial state")
        for atom in init:
            print(atom)
        print()
        print("Goals")
        for goal in goals:
            print(goal)
        for action in actions:
            print()
            print("Action")
            action.dump()
        for axiom in axioms:
            print()
            print("Axiom")
            axiom.dump()
        print()
        print("Axiom layers")
        for atom, layer in axiom_layer_dict.items():
            print("%s: layer %d" % (atom, layer))
    sys.stdout = old_stdout


def translate_task(
    strips_to_sas,
    ranges,
    translation_key,
    mutex_dict,
    mutex_ranges,
    mutex_key,
    init,
    goals,
    actions,
    axioms,
    metric,
    implied_facts,
):
    with timers.timing("Processing axioms", block=True):
        axioms, axiom_init, axiom_layer_dict = axiom_rules.handle_axioms(
            actions, axioms, goals
        )
    init = init + axiom_init

    if options.dump_task:
        # Remove init facts that don't occur in strips_to_sas: they're constant.
        nonconstant_init = filter(strips_to_sas.get, init)
        dump_task(nonconstant_init, goals, actions, axioms, axiom_layer_dict)

    init_values = [rang - 1 for rang in ranges]
    # Closed World Assumption: Initialize to "range - 1" == Nothing.
    for fact in init:
        pairs = strips_to_sas.get(fact, [])  # empty for static init facts
        for var, val in pairs:
            curr_val = init_values[var]
            if curr_val != ranges[var] - 1 and curr_val != val:
                assert False, "Inconsistent init facts! [fact = %s]" % fact
            init_values[var] = val
    init = sas_tasks.SASInit(init_values)

    goal_dict_list = translate_strips_conditions(
        goals, strips_to_sas, ranges, mutex_dict, mutex_ranges
    )
    if goal_dict_list is None:
        # "None" is a signal that the goal is unreachable because it
        # violates a mutex.
        return unsolvable_sas_task("Goal violates a mutex")

    assert len(goal_dict_list) == 1, "Negative goal not supported"
    ## we could substitute the negative goal literal in
    ## normalize.substitute_complicated_goal, using an axiom. We currently
    ## don't do this, because we don't run into this assertion, if the
    ## negative goal is part of finite domain variable with only two
    ## values, which is most of the time the case, and hence refrain from
    ## introducing axioms (that are not supported by all heuristics)
    goal_pairs = list(goal_dict_list[0].items())
    if not goal_pairs:
        return solvable_sas_task("Empty goal")
    goal = sas_tasks.SASGoal(goal_pairs)

    operators = translate_strips_operators(
        actions, strips_to_sas, ranges, mutex_dict, mutex_ranges, implied_facts
    )
    axioms = translate_strips_axioms(
        axioms, strips_to_sas, ranges, mutex_dict, mutex_ranges
    )

    axiom_layers = [-1] * len(ranges)
    for atom, layer in axiom_layer_dict.items():
        assert layer >= 0
        [(var, val)] = strips_to_sas[atom]
        axiom_layers[var] = layer
    variables = sas_tasks.SASVariables(ranges, axiom_layers, translation_key)
    mutexes = [sas_tasks.SASMutexGroup(group) for group in mutex_key]

    return sas_tasks.SASTask(variables, mutexes, init, goal, operators, axioms, metric)


def trivial_task(solvable):
    variables = sas_tasks.SASVariables(
        [2], [-1], [["Atom dummy(val1)", "Atom dummy(val2)"]]
    )
    # We create no mutexes: the only possible mutex is between
    # dummy(val1) and dummy(val2), but the preprocessor would filter
    # it out anyway since it is trivial (only involves one
    # finite-domain variable).
    mutexes = []
    init = sas_tasks.SASInit([0])
    if solvable:
        goal_fact = (0, 0)
    else:
        goal_fact = (0, 1)
    goal = sas_tasks.SASGoal([goal_fact])
    operators = []
    axioms = []
    metric = True
    return sas_tasks.SASTask(variables, mutexes, init, goal, operators, axioms, metric)


def solvable_sas_task(msg):
    print("%s! Generating solvable task..." % msg)
    return trivial_task(solvable=True)


def unsolvable_sas_task(msg):
    print("%s! Generating unsolvable task..." % msg)
    return trivial_task(solvable=False)


def pddl_to_sas(task):
    with timers.timing("Instantiating", block=True):
        (
            relaxed_reachable,
            atoms,
            actions,
            axioms,
            reachable_action_params,
        ) = instantiate.explore(task)

    if not relaxed_reachable:
        return unsolvable_sas_task("No relaxed solution")

    # HACK! Goals should be treated differently.
    if isinstance(task.goal, pddl.Conjunction):
        goal_list = task.goal.parts
    else:
        goal_list = [task.goal]
    for item in goal_list:
        assert isinstance(item, pddl.Literal)

    with timers.timing("Computing fact groups", block=True):
        groups, mutex_groups, translation_key = fact_groups.compute_groups(
            task, atoms, reachable_action_params
        )

    with timers.timing("Building STRIPS to SAS dictionary"):
        ranges, strips_to_sas = strips_to_sas_dictionary(
            groups, assert_partial=options.use_partial_encoding
        )

    with timers.timing("Building dictionary for full mutex groups"):
        mutex_ranges, mutex_dict = strips_to_sas_dictionary(
            mutex_groups, assert_partial=False
        )

    if options.add_implied_preconditions:
        with timers.timing("Building implied facts dictionary..."):
            implied_facts = build_implied_facts(strips_to_sas, groups, mutex_groups)
    else:
        implied_facts = {}

    with timers.timing("Building mutex information", block=True):
        if options.use_partial_encoding:
            mutex_key = build_mutex_key(strips_to_sas, mutex_groups)
        else:
            # With our current representation, emitting complete mutex
            # information for the full encoding can incur an
            # unacceptable (quadratic) blowup in the task representation
            # size. See issue771 for details.
            print("using full encoding: between-variable mutex information skipped.")
            mutex_key = []

    with timers.timing("Translating task", block=True):
        sas_task = translate_task(
            strips_to_sas,
            ranges,
            translation_key,
            mutex_dict,
            mutex_ranges,
            mutex_key,
            task.init,
            goal_list,
            actions,
            axioms,
            task.use_min_cost_metric,
            implied_facts,
        )

    print("%d effect conditions simplified" % simplified_effect_condition_counter)
    print("%d implied preconditions added" % added_implied_precondition_counter)

    if options.filter_unreachable_facts:
        with timers.timing("Detecting unreachable propositions", block=True):
            try:
                simplify.filter_unreachable_propositions(sas_task)
            except simplify.Impossible:
                return unsolvable_sas_task("Simplified to trivially false goal")
            except simplify.TriviallySolvable:
                return solvable_sas_task("Simplified to empty goal")

    if options.reorder_variables or options.filter_unimportant_vars:
        with timers.timing("Reordering and filtering variables", block=True):
            variable_order.find_and_apply_variable_order(
                sas_task, options.reorder_variables, options.filter_unimportant_vars
            )

    # from IPython import embed; embed()

    return sas_task


def build_mutex_key(strips_to_sas, groups):
    assert options.use_partial_encoding
    group_keys = []
    for group in groups:
        group_key = []
        for fact in group:
            represented_by = strips_to_sas.get(fact)
            if represented_by:
                assert len(represented_by) == 1
                group_key.append(represented_by[0])
            else:
                print("not in strips_to_sas, left out:", fact)
        group_keys.append(group_key)
    return group_keys


def build_implied_facts(strips_to_sas, groups, mutex_groups):
    ## Compute a dictionary mapping facts (FDR pairs) to lists of FDR
    ## pairs implied by that fact. In other words, in all states
    ## containing p, all pairs in implied_facts[p] must also be true.
    ##
    ## There are two simple cases where a pair p implies a pair q != p
    ## in our FDR encodings:
    ## 1. p and q encode the same fact
    ## 2. p encodes a STRIPS proposition X, q encodes a STRIPS literal
    ##    "not Y", and X and Y are mutex.
    ##
    ## The first case cannot arise when we use partial encodings, and
    ## when we use full encodings, I don't think it would give us any
    ## additional information to exploit in the operator translation,
    ## so we only use the second case.
    ##
    ## Note that for a pair q to encode a fact "not Y", Y must form a
    ## fact group of size 1. We call such propositions Y "lonely".

    ## In the first step, we compute a dictionary mapping each lonely
    ## proposition to its variable number.
    lonely_propositions = {}
    for var_no, group in enumerate(groups):
        if len(group) == 1:
            lonely_prop = group[0]
            assert strips_to_sas[lonely_prop] == [(var_no, 0)]
            lonely_propositions[lonely_prop] = var_no

    ## Then we compute implied facts as follows: for each mutex group,
    ## check if prop is lonely (then and only then "not prop" has a
    ## representation as an FDR pair). In that case, all other facts
    ## in this mutex group imply "not prop".
    implied_facts = defaultdict(list)
    for mutex_group in mutex_groups:
        for prop in mutex_group:
            prop_var = lonely_propositions.get(prop)
            if prop_var is not None:
                prop_is_false = (prop_var, 1)
                for other_prop in mutex_group:
                    if other_prop is not prop:
                        for other_fact in strips_to_sas[other_prop]:
                            implied_facts[other_fact].append(prop_is_false)

    return implied_facts


def dump_statistics(sas_task):
    print("Translator variables: %d" % len(sas_task.variables.ranges))
    print(
        "Translator derived variables: %d"
        % len([layer for layer in sas_task.variables.axiom_layers if layer >= 0])
    )
    print("Translator facts: %d" % sum(sas_task.variables.ranges))
    print("Translator goal facts: %d" % len(sas_task.goal.pairs))
    print("Translator mutex groups: %d" % len(sas_task.mutexes))
    print(
        "Translator total mutex groups size: %d"
        % sum(mutex.get_encoding_size() for mutex in sas_task.mutexes)
    )
    print("Translator operators: %d" % len(sas_task.operators))
    print("Translator axioms: %d" % len(sas_task.axioms))
    print("Translator task size: %d" % sas_task.get_encoding_size())
    try:
        peak_memory = tools.get_peak_memory_in_kb()
    except Warning as warning:
        print(warning)
    else:
        print("Translator peak memory: %d KB" % peak_memory)


def main():
    if not options.scope_only:
        timer = timers.Timer()
        with timers.timing("Parsing", True):
            task = pddl_parser.open(
                domain_filename=options.domain, task_filename=options.task
            )

        with timers.timing("Normalizing task"):
            normalize.normalize(task)

        if options.generate_relaxed_task:
            # Remove delete effects.
            for action in task.actions:
                for index, effect in reversed(list(enumerate(action.effects))):
                    if effect.literal.negated:
                        del action.effects[index]

        sas_task = pddl_to_sas(task)

        dump_statistics(sas_task)

        with timers.timing("Writing output SAS file"):
            with open(options.sas_file, "w") as output_file:
                sas_task.output(output_file)

    scope_sas(sas_path=options.sas_file)

def scope_sas(sas_path):
    with timers.timing("Reading SAS file"):
        parser = sas_parser.SasParser(pth=sas_path)
        parser.parse()
        sas_task : sas_tasks.SASTask = parser.to_fd()

    timer = timers.Timer()
    if options.scope:
        # This below block of code performs task scoping on the SAS+ domain.
        str2var_dict = scoping_sas_converter.make_str2var_dict(sas_task.variables)
        str_grounded_action_list = scoping_sas_converter.make_str_grounded_actions(
            sas_task.operators
        )
        cae_triples = scoping_sas_converter.str_grounded_actions2skills(
            str_grounded_action_list, str2var_dict
        )
        init_cond_list = scoping_sas_converter.make_init_cond_list(
            sas_task.init.values, str2var_dict
        )
        goal_cond = scoping_sas_converter.make_goal_cond(sas_task.goal.pairs, str2var_dict)
        rel_pvars, cl_pvars, rel_skills = scope(
            goals=goal_cond, skills=cae_triples, start_condition=init_cond_list
        )
        sas_file_scoped = get_scoped_file_path(options.sas_file)

        def strip_parens(s):
            return s.replace('(', '').replace(')', '')

        # Make a set for rel pvars and rel actions so that we can lookup amongst these quickly during writeback
        rel_skill_names = set()
        for rel_skill in rel_skills:
            if type(rel_skill.action) == str:
                rel_skill_names.add(strip_parens(rel_skill.action))
            elif type(rel_skill.action) == list:
                for skill_name in rel_skill.action:
                    rel_skill_names.add(strip_parens(skill_name))
        rel_pvars_names = set()
        for pvar in rel_pvars:
            rel_pvars_names.add(str(pvar)[:-2])

        if options.write_erfs:
            # Get 'effectively relevant' pvars - pvars that appear in at least one precondition and at least one effect.
            # These are used to estimate size of effective state space of scoped domain.
            # We do this because we do not in fact remove fluents from the sas+ domain, we only remove operators
            def get_effectively_relevant_pvars(
                cae_triples: Iterable[SkillPDDL], action_names = None
            ):
                """
                :param cae_triples: operators from original domain
                :param action_names: names of operators in scoped domain
                Return 'effectively relevant' pvars - pvars that are both conditioned on and affected.
                The reasoning is that if a pvar is never conditioned on, we don't care about it. If it is never affected, we can't care about it.
                Hopefully this let's us estimate the effective state space of a domain.
                """
                affected_pvars_str = []
                conditioned_pvars_str = []
                for cae in cae_triples:
                    if action_names is None or cae.action in action_names:
                        for (
                            eff
                        ) in (
                            cae.all_effects
                        ):  # cae is concrete, so we could just use .effects
                            affected_pvars_str.append(eff.pvar_str)
                            conditioned_pvars_str.extend(get_atoms(cae.precondition))
                affected_pvars_str = set(affected_pvars_str)
                conditioned_pvars_str = set(map(str, conditioned_pvars_str))
                effectively_relevant_pvars = sorted(
                    [x for x in affected_pvars_str if x in conditioned_pvars_str]
                )
                erf = []
                for x in effectively_relevant_pvars:
                    if x[-2:] == "()":
                        x = x[:-2]
                    erf.append(x)
                return erf

            erf = get_effectively_relevant_pvars(cae_triples)
            with open(
                get_effectively_relevant_fluents_file_path(options.sas_file), "w"
            ) as f:
                f.write("\n".join(erf))

            # Add parentheses around skill name to match with cae action names
            rel_skill_names_with_parens = ["(" + a + ")" for a in rel_skill_names]
            erf_scoped = get_effectively_relevant_pvars(
                cae_triples, rel_skill_names_with_parens
            )
            with open(
                get_effectively_relevant_fluents_file_path(sas_file_scoped), "w"
            ) as f:
                f.write("\n".join(erf_scoped))

            print(f"Original efectively relevant fluents: {len(erf)}")
            print(f"Scoped efectively relevant fluents: {len(erf_scoped)}")

        # Now, writeback the scoped SAS file
        writeback_scoped_sas(
            rel_skill_names, rel_pvars_names, options.sas_file, sas_file_scoped
        )
        # End task scoping block

    if options.sas_file_correct is not None:
        with open(options.sas_file_correct, "r") as f:
            sas_correct_str = f.read()
        with open(options.sas_file, "r") as f:
            sas_scoped_str = f.read()
        scoped_correctly = sas_correct_str == sas_scoped_str
        print(f"Scoped correctly: {scoped_correctly}")

    print("Done! %s" % timer)


def handle_sigxcpu(signum, stackframe):
    print()
    print("Translator hit the time limit")
    # sys.exit() is not safe to be called from within signal handlers, but
    # os._exit() is.
    os._exit(TRANSLATE_OUT_OF_TIME)


def main_from_other_script(**kwargs):
    """
    Used to run translate and scope from another script.
    """
    global options
    for k, v in kwargs.items():
        setattr(options, k, v)

    try:
        signal.signal(signal.SIGXCPU, handle_sigxcpu)
    except AttributeError:
        print(
            "Warning! SIGXCPU is not available on your platform. "
            "This means that the planner cannot be gracefully terminated "
            "when using a time limit, which, however, is probably "
            "supported on your platform anyway."
        )
    try:
        # Reserve about 10 MB of emergency memory.
        # https://stackoverflow.com/questions/19469608/
        emergency_memory = b"x" * 10**7
        scope_sas()

        # main()
    except MemoryError:
        del emergency_memory
        print()
        print("Translator ran out of memory, traceback:")
        print("=" * 79)
        traceback.print_exc(file=sys.stdout)
        print("=" * 79)
        sys.exit(TRANSLATE_OUT_OF_MEMORY)


if __name__ == "__main__":
    try:
        signal.signal(signal.SIGXCPU, handle_sigxcpu)
    except AttributeError:
        print(
            "Warning! SIGXCPU is not available on your platform. "
            "This means that the planner cannot be gracefully terminated "
            "when using a time limit, which, however, is probably "
            "supported on your platform anyway."
        )
    try:
        # Reserve about 10 MB of emergency memory.
        # https://stackoverflow.com/questions/19469608/
        emergency_memory = b"x" * 10**7
        main()

        # main()
    except MemoryError:
        del emergency_memory
        print()
        print("Translator ran out of memory, traceback:")
        print("=" * 79)
        traceback.print_exc(file=sys.stdout)
        print("=" * 79)
        sys.exit(TRANSLATE_OUT_OF_MEMORY)