#!/usr/bin/env bash

# generate data training set from 'quartiers.csv' --> /data/quartiers_training_set.csv / /data/quartiers_training_labels.pickle
# create an embedding for the close vocabulary of the generated training set --> /data/quartiers_embedding.pth
python -m fofe_entity_linking.dataset \
--source_data_path ./fofe_entity_linking/quartiers.csv --output_path ./fofe_entity_linking/data --text_column EntityMention --label_column EntityName --verbose True \
--embedding_dim 64 \
--embedding_hidden_layer_size 384 \
--embedding_ngram_size 2 \
--embedding_learning_rate 0.0005 \
--embedding_epochs 150 \

# train the FOFE-based Neural Networks to classify text to the 31 classes (Montreal's quartiers)
python -m fofe_entity_linking.train \
--model_name quartiers \
--output ./fofe_entity_linking/models \
--hidden_layer_size 1536 \
--fofe_forgetting_factor 0.95 \
--ngram_size 2 \
--dropout_rate 0.25 \
--epochs 50 \
--learning_rate 0.0005 \
--batch_size 64 \
--schedule 10 \
--patience 200 \
--number_of_classes 31 \
--data_path ./fofe_entity_linking/data/quartiers_training_set.csv \
--data_testset_path ./fofe_entity_linking/data/quartiers_test_set.csv \
--label_weight_path ./fofe_entity_linking/data/quartiers_training_labels.pickle \
--embedding_path ./fofe_entity_linking/data/quartiers_embedding.pth \
--vocab_path ./fofe_entity_linking/data/quartiers_vocab.pickle
