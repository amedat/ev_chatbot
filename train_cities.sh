#!/usr/bin/env bash

# generate data training set from 'metro.csv' --> ./fofe_entity_linking/data/metro_training_set.csv / ./fofe_entity_linking/data/metro_training_labels.pickle
# create an embedding for the close vocabulary of the generated training set --> ./fofe_entity_linking/data/metro_embedding.pth
python -m fofe_entity_linking.dataset \
--source_data_path ./fofe_entity_linking/cities.csv --output_path ./fofe_entity_linking/data --text_column EntityMention --label_column EntityName --verbose True \
--embedding_dim 256 \
--embedding_hidden_layer_size 1024 \
--embedding_ngram_size 2 \
--embedding_learning_rate 0.0005 \
--embedding_epochs 2 \

# train the FOFE-based Neural Networks to classify text to the 871 classes (Province of Quebec's cities)
python -m fofe_entity_linking.train \
--model_name cities \
--output ./fofe_entity_linking/models \
--hidden_layer_size 2048 \
--fofe_forgetting_factor 0.95 \
--ngram_size 2 \
--dropout_rate 0.25 \
--epochs 2 \
--learning_rate 0.0005 \
--batch_size 128 \
--schedule 10 \
--patience 200 \
--number_of_classes 869 \
--data_path ./fofe_entity_linking/data/cities_training_set.csv \
--data_testset_path ./fofe_entity_linking/data/cities_test_set.csv \
--label_weight_path ./fofe_entity_linking/data/cities_training_labels.pickle \
--embedding_path ./fofe_entity_linking/data/cities_embedding.pth \
--vocab_path ./fofe_entity_linking/data/cities_vocab.pickle