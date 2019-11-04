#!/usr/bin/env bash
source activate evchatbot

# generate data training set from 'metro.csv' --> ./data/metro_training_set.csv / ./data/metro_training_labels.pickle
# create an embedding for the close vocabulary of the generated training set --> ./data/metro_embedding.pth
python dataset.py \
--source_data_path ./metro.csv --output_path ./data --text_column EntityMention --label_column EntityName --verbose True \
--embedding_dim 64 \
--embedding_hidden_layer_size 384 \
--embedding_ngram_size 2 \
--embedding_learning_rate 0.0005 \
--embedding_epochs 150 \

# train the FOFE-based Neural Networks to classify text to the 68 classes (Montreal's metro stations)
python train.py \
--model_name metro \
--hidden_layer_size 1536 \
--fofe_forgetting_factor 0.95 \
--ngram_size 2 \
--dropout_rate 0.25 \
--epochs 50 \
--learning_rate 0.0005 \
--batch_size 64 \
--schedule 10 \
--patience 200 \
--number_of_classes 68 \
--data_path ./data/metro_training_set.csv \
--data_testset_path ./data/metro_test_set.csv \
--label_weight_path ./data/metro_training_labels.pickle \
--embedding_path ./data/metro_embedding.pth \
--vocab_path ./data/metro_vocab.pickle
