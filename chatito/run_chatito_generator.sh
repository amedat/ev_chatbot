#!/usr/bin/env bash
#
# Chatito
# https://github.com/rodrigopivi/Chatito
#
# Generate datasets for AI chatbots, NLP tasks, named entity recognition or
# text classification models using a simple DSL!
#
# Chatito supports Node.js v8.11.2 LTS or higher
#

# set current working directory to the directory of the script?
cd "$(dirname "$0")"

# run nodejs chatito, loading /input/*.chatito to generate /output/rasa_dataset_training.json
npx chatito ./input --format=rasa --outputPath=output
