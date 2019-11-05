import argparse
import pickle
import torch

from .dataset import DatasetGenerator
from .embedding import NgramEmbedding, Fofe
from .model import FofeNNModel


use_cuda = torch.cuda.is_available()


def load_models(model_pathname, embedding_pathname, vocab_filename):
    e = NgramEmbedding(embedding_filename=embedding_pathname, vocab_filename=vocab_filename)

    load_dict = torch.load(model_pathname, map_location=torch.device('cpu'))
    hidden_layer_size = len(load_dict['fc1.bias'])
    number_of_classes = len(load_dict['fc2.bias'])
    m = FofeNNModel(e.embedding_layer.embedding_dim, hidden_layer_size, 0.25, number_of_classes)
    m.load_state_dict(load_dict)

    m.eval()
    return m, e


def predict(model, embedding, text, max_tokens=50):
    # process input text
    fofe_input = get_fofe_embedding(embedding, text, max_tokens)
    processed_input = fofe_input.unsqueeze(0)

    if use_cuda:
        processed_input = processed_input.to('cuda')
        model = model.to('cuda')

    probabilities = model(processed_input)

    return probabilities


def get_fofe_embedding(embedding, text, max_tokens):
    normalized_text = DatasetGenerator.normalize_name(text)

    # get the indices list of the normalized text
    sentence_indices = embedding.ngram.ngram_indexes(normalized_text)

    if len(sentence_indices) > max_tokens:
        sentence_indices = sentence_indices[max_tokens]

    sentence_v = [embedding.embedding_layer.weight[i].numpy() for i in sentence_indices]

    # convert one-hot to FOFE encoding
    fofe = Fofe(0.95)
    return fofe.encode_sentence(sentence_v)


if __name__ == "__main__":
    parser = argparse.ArgumentParser('Testing a pre-trained FOFE-based NN for text classification')
    parser.add_argument('--model', type=str, help='path for pre-trained model')
    parser.add_argument('--embedding', type=str, help="path for pre-trained model's embedding")
    parser.add_argument('--labels', type=str, help="path for pre-trained model's labels")
    parser.add_argument('--vocab', type=str, help="path for pre-trained model's labels")

    parser.add_argument('--text', type=str, default='Roberval', help='text string')
    parser.add_argument('--max_length', type=int, default=50)

    args = parser.parse_args()

    model, embedding = load_models(args.model, args.embedding, args.vocab)
    prediction = predict(model, embedding, args.text, args.max_length)

    print(f'prediction : {prediction}')
    print(f'input : {args.text}\n')

    if args.labels:
        labels, label2idx, _ = pickle.load(open(args.labels, "rb"))

        # max
        max = prediction.argmax(1)[0]
        print(f'predicted argmax: {max}')
        print(f'predicted label: {labels[max]}\n')

        # top-k
        values, indices = prediction.topk(5)
        for rank, indice in enumerate(indices[0]):
            print(f'top {rank+1}: {labels[indice]}')
