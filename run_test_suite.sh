#!/usr/bin/env bash

echo -----------------------------------------
echo Test Rasa NLU
echo -----------------------------------------
rasa test nlu --nlu ./tests/rasa_dataset_testing.json \
              --report ./tests/results/nlu \
              --errors ./tests/results/nlu/errors.json \
              --confmat ./tests/results/nlu/intent_confusion_matrix.png \
              --histogram ./tests/results/nlu/intent_prediction_confidence_histogram.png

if [ "$?" == "127" ]; then
	echo "Can't find rasa cli, make sure you activated the correct conda environment."
	echo "Current conda environment is:"
	echo $CONDA_DEFAULT_ENV
	exit 1
fi
