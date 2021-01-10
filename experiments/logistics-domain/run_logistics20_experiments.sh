#!/bin/bash

# Usage: (from repository root, run) ./experiments/logistics-domain/run_logistics_experiments.sh <num_trials> <path to FD installation>
# Example: 
TIMEFORMAT=%R
declare -a sruntimes
user_arg="$1"

# The counter needs to be 1 + num_trials you want for the experiment, because the first trial is slightly slower due to needing to execute
# some of the setup bash commands. Thus, take all readings except the first!
COUNTER="$user_arg + 1"
until [ $COUNTER -lt 1 ]; do
    echo RUN_NUMBER $COUNTER
    exec 3>&1 4>&2
    foo=$( { time python downward_translate/translate_and_scope.py examples/IPC_domains_propositional/logistics00/domain.pddl examples/IPC_domains_propositional/logistics00/prob20.pddl --sas-file logistics20.sas 1>&3 2>&4; } 2>&1 )  # Captures time only.
    exec 3>&- 4>&-
    sruntimes+=("$foo")
    let COUNTER-=1
done

declare -a fd_runtimes
COUNTER="$user_arg + 1"
until [ $COUNTER -lt 1 ]; do
    echo RUN_NUMBER $COUNTER
    exec 3>&1 4>&2
    foo=$( { time python $2 --alias seq-opt-lmcut /home/nishanth/Documents/planutils_stuff/OO-Scoping-IPC/logistics20.sas 1>&3 2>&4; } 2>&1 )  # Captures time only.
    exec 3>&- 4>&-
    fd_runtimes+=("$foo")
    let COUNTER-=1
done

declare -a sfd_runtimes
COUNTER="$user_arg + 1"
until [ $COUNTER -lt 1 ]; do
    echo RUN_NUMBER $COUNTER
    exec 3>&1 4>&2
    foo=$( { time python $2 --alias seq-opt-lmcut /home/nishanth/Documents/planutils_stuff/OO-Scoping-IPC/logistics20_scoped.sas 1>&3 2>&4; } 2>&1 )  # Captures time only.
    exec 3>&- 4>&-
    sfd_runtimes+=("$foo")
    let COUNTER-=1
done

echo
echo TIME_TAKEN_FOR_SCOPING_FOR_EACH_TRIAL
# Print the times taken for scoping valid trials
echo "${sruntimes[@]:1}"
echo
echo TIME_TAKEN_FOR_RAW_PLANNING_FOR_EACH_TRIAL
# Print the times taken for raw planning on all valid trials
echo "${fd_runtimes[@]:1}"
echo
echo TIME_TAKEN_FOR_SCOPED_PLANNING_FOR_EACH_TRIAL
echo "${sfd_runtimes[@]:1}"
