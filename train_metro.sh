#!/usr/bin/env bash

# generate data training set from 'metro.csv' --> /data/metro_training_set.csv / /data/metro_training_labels.pickle
# create an embedding for the close vocabulary of the generated training set --> /data/metro_embedding.pth
python -m fofe_entity_linking.dataset \
--source_data_path ./fofe_entity_linking/metro.csv --output_path ./fofe_entity_linking/data --text_column EntityMention --label_column EntityName --verbose True \
--embedding_dim 64 \
--embedding_hidden_layer_size 384 \
--embedding_ngram_size 2 \
--embedding_learning_rate 0.0005 \
--embedding_epochs 2 \

# train the FOFE-based Neural Networks to classify text to the 68 classes (Montreal's metro stations)
python -m fofe_entity_linking.train \
--model_name metro \
--output ./fofe_entity_linking/models \
--hidden_layer_size 1536 \
--fofe_forgetting_factor 0.95 \
--ngram_size 2 \
--dropout_rate 0.25 \
--epochs 2 \
--learning_rate 0.0005 \
--batch_size 64 \
--schedule 10 \
--patience 200 \
--number_of_classes 68 \
--data_path ./fofe_entity_linking/data/metro_training_set.csv \
--data_testset_path ./fofe_entity_linking/data/metro_test_set.csv \
--label_weight_path ./fofe_entity_linking/data/metro_training_labels.pickle \
--embedding_path ./fofe_entity_linking/data/metro_embedding.pth \
--vocab_path ./fofe_entity_linking/data/metro_vocab.pickle
