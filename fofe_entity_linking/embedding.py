import pickle
import unidecode

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


class Fofe(object):
    """
    Implementation of FOFE (Fixed-Size Ordinally-Forgetting Encoding).

    Notebook documentation:
        ./notebooks/FOFE Encoding.ipynb

    Fixed-size ordinally-forgetting encoding (FOFE) method,
    which can almost uniquely encode any variable-length sequence of words into a fixed-size representation.
    FOFE can model the word order in a sequence using a simple ordinally-forgetting mechanism
    according to the positions of words.

    Paper:
        The Fixed-Size Ordinally-Forgetting Encoding Method for Neural Network Language Models
            Shiliang Zhang , Hui Jiang , Mingbin Xu, Junfeng Hou, Lirong Dai
            https://www.aclweb.org/anthology/P15-2081.pdf
    """

    def __init__(self, forgetting_factor=0.5):
        """
        Arguments
            forgetting_factor - float, forgetting factor (alpha value) between 0 and 1 exclusively
        """
        self.forgetting_factor = forgetting_factor
        self.m = self.compute_matrices()

    def encode_sentence(self, sentence_onehot):
        token_count = len(sentence_onehot)
        v = torch.tensor(sentence_onehot, dtype=torch.float32)
        s = self.m[token_count].mm(v)

        # return the sentence encoding (last row)
        return s[-1]

    def compute_matrices(self, number_of_matrices=50):
        """
        Returns a list of tensor matrix.

        Arguments
            number_of_matrices: the number of matrices to create (a matrix per power order)
        """
        m = []
        for matrix_order in range(number_of_matrices):
            m.append(self.compute_m_matrix(matrix_order))
        return m

    def compute_m_matrix(self, matrix_order):
        """
        Returns a tensor matrix of the specified order.
        Here is an example for matrix of order 6 and a forgetting factor ff:
            [[1,     0,     0,     0,     0,     0],
             [ff**1, 1,     0,     0,     0,     0],
             [ff**2, ff**1, 1,     0,     0,     0],
             [ff**3, ff**2, ff**1, 1,     0,     0],
             [ff**4, ff**3, ff**2, ff**1, 1,     0],
             [ff**5, ff**4, ff**3, ff**2, ff**1, 1],
            ]

        Arguments
            matrix_order - integer, the order of the lower triangular matrix
        Returns
            numpy array, the lower triangular matrix of shape (order, order)
        """
        # starts with an all zero matrix of the correct size
        m = torch.zeros((matrix_order, matrix_order), dtype=torch.float32)

        # fill the lower triangle with power of the forgetting factor (ff)
        for c in range(matrix_order):  # loop over each columns
            p = 0  # reset power value
            for r in range(matrix_order):  # loop over each rows
                if r >= c:
                    m[r, c] = self.forgetting_factor ** p
                    p += 1
        return m


class NgramHashing(object):

    def __init__(self, n=None, corpus_filename=None, corpus_text_list=None, vocab_filename=None):
        """
          n - Integer, the number of character in the ngram
          corpus_filename -
          corpus_text_list -
          vocab_filename -
        """
        if vocab_filename:
            # load vocab
            with open(vocab_filename, "rb") as input_file:
                self.vocab = pickle.load(input_file)
            self.n = len(self.vocab[0])
        else:
            # read the file line by line to create the word corpus
            if corpus_filename:
                with open(corpus_filename) as f:
                    corpus_text_list = f.readlines()

            corpus = self.get_preprocessed_lines(corpus_text_list)

            self.n = n
            self.vocab = self._create_vocab(corpus)

        self.ngram2idx = {ngram: i for i, ngram in enumerate(self.vocab)}

    def save_vocab(self, ngram_vocab_filename):
        with open(ngram_vocab_filename, "wb") as out:
            pickle.dump(self.vocab, out)

    def ngram(self, str):
        ngram_list = []
        word = '#' + self.ascii_trim_lowercase(str) + '#'
        for i in range(len(word) - self.n + 1):
            ngram = word[i:i + self.n]
            # add the ngram if part of the vocab, otherwise OOV
            ngram_list.append(ngram if ngram in self.vocab else '#'*self.n)
        return ngram_list

    def ngram_indexes(self, str):
        ngram_list = self.ngram(str)
        return [self.ngram2idx.get(ngram) for ngram in ngram_list]

    def _create_vocab(self, corpus):
        # first token of the vocab is OOV (out of vocab) token
        vocab = ['#'*self.n]

        for word in corpus:
            word = '#' + word + '#'
            for i in range(len(word) - self.n + 1):
                ngram = word[i:i + self.n]
                if ngram not in vocab and '_' not in ngram:
                    vocab.append(ngram)
        return vocab

    @staticmethod
    def ascii_trim_lowercase(text):
        """ convert the given text to ascii (remove accent), remove leading spaces and lowercase. """
        return unidecode.unidecode(text).strip().lower()

    def get_preprocessed_lines(self, corpus_text_list):
        """ read the given file and returns a list of lines, convert to ascii without leading spaces """
        return [self.ascii_trim_lowercase(x) for x in corpus_text_list]


class NGramLanguageModeler(nn.Module):

    def __init__(self, vocab_size, embedding_dim, context_size, hidden_size=128):
        super(NGramLanguageModeler, self).__init__()

        self.embedding_layer = nn.Embedding(vocab_size, embedding_dim)
        self.linear1 = nn.Linear(context_size * embedding_dim, hidden_size)
        self.linear2 = nn.Linear(hidden_size, vocab_size)

    def forward(self, inputs):
        embeds = self.embedding_layer(inputs).view((1, -1))
        out = F.relu(self.linear1(embeds))
        out = self.linear2(out)
        log_probs = F.log_softmax(out, dim=1)
        return log_probs


class NgramEmbedding(object):

    def __init__(self, embedding_filename=None, vocab_filename=None, ngram=None):
        self.embedding_layer = None
        if embedding_filename:
            # load objects
            self.embedding_layer = torch.load(embedding_filename)

        self.ngram = ngram if ngram else None

        if not ngram and vocab_filename:
            self.ngram = NgramHashing(vocab_filename=vocab_filename)

    def save(self, embedding_layer_weights_filename, ngram_vocab_filename):
        # save the trained embedding layer weights
        torch.save(self.embedding_layer.cpu(), embedding_layer_weights_filename)

        # save the ngram vocabulary
        self.ngram.save_vocab(ngram_vocab_filename)

    def train_ngram(self, training_sentence, nb_epochs, embedding_dim=16, context_size=2, hidden_size=128, lr=0.0001, verbose=False):
        """
          Train the language model.

          vocab_list: List, vocab ngram list. ex: ['##', '#v', 've', 'er', 'rd', 'du', 'un', 'n#']
          training_sentence: String, a long string of token to train the language model.
                             ex: ['#v', 've', 'er', 'rd', 'du', 'un', 'n#', '#p', 'pi', 'ie', 'e-', '-i', 'ix', 'x#']
          nb_epochs: Integer, the number of training epoch
          verbose: Boolean, true to print log info
        """
        if verbose:
            print(f"\n--- training language model (embedding) ---")

        # define vocab words list
        self.vocab_tokens = self.ngram.vocab
        self.token_to_idx = {token: i for i, token in enumerate(self.vocab_tokens)}

        # Each tuple is ([word_i - 2, word_i - 1], target word) ex:
        # [(['#v', 've'], 'er'), (['ve', 'er'], 'rd'), (['er', 'rd'], 'du')]
        trigrams = [([training_sentence[i], training_sentence[i + 1]], training_sentence[i + 2])
                    for i in range(len(training_sentence) - 2)]

        losses = []
        loss_function = nn.NLLLoss()
        model = NGramLanguageModeler(len(self.vocab_tokens), embedding_dim, context_size, hidden_size)
        optimizer = optim.Adam(model.parameters(), lr=lr)

        use_cuda = torch.cuda.is_available()
        if use_cuda:
            model.cuda()

        for epoch in range(nb_epochs):
            total_loss = 0
            for context, target in trigrams:
                # Prepare the inputs to be passed to the model
                # (i.e, turn the tokens into integer indices and wrap them in tensors)
                context_idxs = torch.tensor([self.token_to_idx[i] for i in context], dtype=torch.long)

                target_tensor = torch.tensor([self.token_to_idx[target]], dtype=torch.long)

                model.zero_grad()

                if use_cuda:
                    context_idxs = context_idxs.cuda()
                    target_tensor = target_tensor.cuda()

                # Run the forward pass, getting log probabilities over next tokens
                log_probs = model(context_idxs)

                # Compute your loss function. (Again, Torch wants the target word wrapped in a tensor)
                loss = loss_function(log_probs, target_tensor)

                # Do the backward pass and update the gradient
                loss.backward()
                optimizer.step()

                # Get the Python number from a 1-element Tensor by calling tensor.item()
                total_loss += loss.item()

            losses.append(total_loss)
            if verbose:
                print(f'epoch {epoch + 1}: loss {total_loss}')

        self.embedding_layer = model.embedding_layer

        # freeze the embedding layer so it won't be update when attach to another network
        # see https://discuss.pytorch.org/t/how-to-exclude-embedding-layer-from-model-parameters/1283/4
        self.embedding_layer.weight.requires_grad = False
