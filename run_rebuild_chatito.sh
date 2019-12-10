#!/usr/bin/env bash
echo -----------------------------------------
echo Generate Rasa NLU JSON from Chatito files
echo -----------------------------------------
./chatito/run_chatito_generator.sh

echo -----------------------------------------
echo Add Lookup Tables to NLU JSON
echo -----------------------------------------
if ! ./chatito/run_add_lookup_table.sh; then
    exit -1
fi

echo -----------------------------------------
echo Copy new NLU JSON over current Rasa NLU
echo -----------------------------------------
cp -v ./chatito/output/rasa_dataset_training.json ./data/
cp -v ./chatito/output/rasa_dataset_testing.json ./tests/

echo -----------------------------------------
echo Train Rasa NLU
echo -----------------------------------------
rasa train --force

if [ "$?" == "127" ]; then
	echo "Can't find rasa cli, make sure you activated the correct conda environment."
	echo "Current conda environment is:"
	echo $CONDA_DEFAULT_ENV
	exit 1
fi
