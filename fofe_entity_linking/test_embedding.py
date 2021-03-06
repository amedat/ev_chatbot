import unittest
import os
import torch

import numpy as np

from embedding import NgramHashing, NgramEmbedding, Fofe


class TestWordHashing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """ This is called before tests in an individual class are run. """
        with open("test_word_hashing.csv", "w") as text_file:
            text_file.write("Verdun\nPie-IX")

        cls.test_trigram = NgramHashing(2, "test_word_hashing.csv")

    @classmethod
    def tearDownClass(cls):
        """ A class method called after tests in an individual class have run. """
        try:
            # delete files generated by the prior tests
            for filename in ['test_word_hashing.csv', 'test_embedding.pth', 'test_vocab.pickle']:
                if os.path.isfile(filename):
                    os.remove(filename)
        except OSError as oserr:
            print(oserr)

    def setUp(self):
        """ This is called immediately before calling the test method. """
        pass

    def test_fofe_matrix_6th_order(self):
        """ This is called before tests in an individual class are run. """
        ff = 0.5
        fofe = Fofe(ff)

        m6 = torch.tensor([[1, 0, 0, 0, 0, 0],
                           [ff ** 1, 1, 0, 0, 0, 0],
                           [ff ** 2, ff ** 1, 1, 0, 0, 0],
                           [ff ** 3, ff ** 2, ff ** 1, 1, 0, 0],
                           [ff ** 4, ff ** 3, ff ** 2, ff ** 1, 1, 0],
                           [ff ** 5, ff ** 4, ff ** 3, ff ** 2, ff ** 1, 1],
                           ], dtype=torch.float32)

        self.assertTrue((m6.numpy() == fofe.m[6].numpy()).all())

    def test_fofe_sentence_encoding(self):
        # vocab of 7 one-hot vectors
        vocab_onehot_embedding = np.eye(7)

        ff = 0.5
        fofe = Fofe(ff)

        expected_fofe_encoding = torch.tensor([ff ** 2, 0, 0, 0, 1 + ff ** 4, ff + ff ** 3, ff ** 5], dtype=torch.float32)

        sentence_onehot = [vocab_onehot_embedding[i] for i in [6, 4, 5, 0, 5, 4]]
        encoding = fofe.encode_sentence(sentence_onehot)

        self.assertTrue(expected_fofe_encoding.equal(encoding))

    def test_vocab_oov(self):
        # test vocab created
        self.assertGreater(len(self.test_trigram.vocab), 0)
        self.assertEqual(self.test_trigram.vocab[0], '##')

    def test_vocab(self):
        self.assertEqual(len(self.test_trigram.vocab), 15)
        self.assertEqual(self.test_trigram.vocab,
                         ['##', '#v', 've', 'er', 'rd', 'du', 'un', 'n#', '#p', 'pi', 'ie', 'e-', '-i', 'ix', 'x#'])

    def test_word_hashing(self):
        self.assertEqual(self.test_trigram.ngram('Verdun'), ['#v', 've', 'er', 'rd', 'du', 'un', 'n#'])
        self.assertEqual(self.test_trigram.ngram('Ver_un'), ['#v', 've', 'er', '##', '##', 'un', 'n#'])
        self.assertEqual(self.test_trigram.ngram('Ve_dun'), ['#v', 've', '##', '##', 'du', 'un', 'n#'])
        self.assertEqual(self.test_trigram.ngram('_erdun'), ['##', '##', 'er', 'rd', 'du', 'un', 'n#'])

    def test_word_hashing_indexes(self):
        self.assertEqual(self.test_trigram.ngram_indexes('Verdun'), [1, 2, 3, 4, 5, 6, 7])

    def test_embedding_lm_training(self):
        training_sentence = self.test_trigram.ngram('Verdun') + self.test_trigram.ngram('Pie-IX')

        ngram_embedding = NgramEmbedding(ngram=self.test_trigram)
        ngram_embedding.train_ngram(training_sentence, 10, verbose=True)

        self.assertIsNotNone(ngram_embedding.embedding_layer)

    def test_embedding_save_load(self):
        empty_embedding = NgramEmbedding()
        self.assertIsNone(empty_embedding.embedding_layer)

        # create and train an embedding
        training_sentence = self.test_trigram.ngram('Verdun') + self.test_trigram.ngram('Pie-IX')
        trained_embedding = NgramEmbedding(ngram=self.test_trigram)
        trained_embedding.train_ngram(training_sentence, 100, embedding_dim=8, verbose=False)
        trained_embedding.save('test_embedding.pth', 'test_vocab.pickle')

        # store embedding for index 1
        index_tensor = torch.tensor([1], dtype=torch.long)
        embedding_tensor_after_training = trained_embedding.embedding_layer(index_tensor)

        # reload embedding
        loaded_embedding = NgramEmbedding(embedding_filename='test_embedding.pth',
                                          vocab_filename='test_vocab.pickle')
        self.assertIsNotNone(loaded_embedding.ngram)
        self.assertIsNotNone(loaded_embedding.embedding_layer)

        # get embedding for index 1 (using loaded embedding layer)
        embedding_tensor_after_loading = loaded_embedding.embedding_layer(index_tensor)

        # make sure both embedding tensors are the same
        self.assertTrue(embedding_tensor_after_loading.equal(embedding_tensor_after_training))

        print(f"embedding for vocab index 1:\n{embedding_tensor_after_training.numpy()[0]}")

        embedding_from_weights = trained_embedding.embedding_layer.weight[1].numpy()
        print(f"embedding from weight for vocab index 1:\n{embedding_from_weights}")

        # check embedding dim
        self.assertEqual(8, loaded_embedding.embedding_layer.embedding_dim)

        # check number of embeddings
        self.assertEqual(len(self.test_trigram.vocab), loaded_embedding.embedding_layer.num_embeddings)


if __name__ == '__main__':
    unittest.main()
