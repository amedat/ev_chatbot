#!/usr/bin/env bash
#source activate evchatbot

# generate data training set from 'metro.csv' --> ./data/metro_training_set.csv / ./data/metro_training_labels.pickle
# create an embedding for the close vocabulary of the generated training set --> ./data/metro_embedding.pth
python dataset.py \
--source_data_path ./cities.csv --output_path ./data --text_column EntityMention --label_column EntityName --verbose True \
--embedding_dim 256 \
--embedding_hidden_layer_size 1024 \
--embedding_ngram_size 2 \
--embedding_learning_rate 0.0005 \
--embedding_epochs 15 \

# train the FOFE-based Neural Networks to classify text to the 871 classes (Province of Quebec's cities)
python train.py \
--model_name cities \
--hidden_layer_size 2048 \
--fofe_forgetting_factor 0.95 \
--ngram_size 2 \
--dropout_rate 0.25 \
--epochs 50 \
--learning_rate 0.0005 \
--batch_size 128 \
--schedule 10 \
--patience 200 \
--number_of_classes 869 \
--data_path ./data/cities_training_set.csv \
--data_testset_path ./data/cities_test_set.csv \
--label_weight_path ./data/cities_training_labels.pickle \
--embedding_path ./data/cities_embedding.pth \
--vocab_path ./data/cities_vocab.pickle