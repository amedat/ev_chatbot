import argparse
import io
import os
import pickle
import random
import re
import unidecode

import numpy as np
import pandas as pd

from io import StringIO
from torch.utils.data import Dataset

# from fofe_entity_linking.embedding import NgramHashing, NgramEmbedding, Fofe
from .embedding import NgramHashing, NgramEmbedding, Fofe


class FofeDataset(Dataset):

    def __init__(self, data_filename, text_column, label_column, encoding, number_of_classes,
                 ngram=2, max_tokens=50, forgetting_factor=0.5, embedding=None):
        self.max_tokens = max_tokens
        self.num_classes = number_of_classes
        self.embedding = embedding

        # read csv file using pandas dataframe
        df = pd.read_csv(data_filename, usecols=[text_column, label_column], encoding=encoding)
        self.texts  = df[text_column].tolist()
        self.labels = df[label_column].tolist()
        self.length = len(self.labels)

        # build vocab by hashing words in ngrams
        self.ngram_hashing = embedding.ngram if embedding else NgramHashing(ngram, corpus_text_list=self.texts)
        self.vocab = self.ngram_hashing.vocab
        self.vocab_size = len(self.vocab)
        self.embedding_dim = embedding.embedding_layer.embedding_dim if embedding else self.vocab_size

        self.vocab_onehot_embedding = np.eye(len(self.vocab))
        self.fofe = Fofe(forgetting_factor)

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        raw_text = self.texts[index]
        normalized_text = DatasetGenerator.normalize_name(raw_text)

        # get the indices list of the normalized text
        sentence_indices = self.ngram_hashing.ngram_indexes(normalized_text)

        if len(sentence_indices) > self.max_tokens:
            sentence_indices = sentence_indices[:self.max_tokens]

        if self.embedding:
            sentence_v = [self.embedding.embedding_layer.weight[i].numpy() for i in sentence_indices]
        else:
            # convert indices to one-hot
            sentence_v = [self.vocab_onehot_embedding[i] for i in sentence_indices]

        # convert one-hot to FOFE encoding
        fofe_encoding = self.fofe.encode_sentence(sentence_v)

        return fofe_encoding, self.labels[index]


class DatasetGenerator(object):

    def __init__(self, input_filename, basic_functions, expanding_functions, max_mixup=10):
        self.max_mixup = max_mixup

        # parse labels and create label to indexes
        self.labels = self.get_entity_list(input_filename)
        # sort by length to make sure string like "Saint-Philippe" will appear before "Chute-Saint-Philippe"
        self.labels.sort(key=len)

        self.label2idx = {label: i for i, label in enumerate(self.labels)}

        # extract 'metro' from './somedir/metro.csv'
        self.base_filename = os.path.splitext(os.path.basename(input_filename))[0]

        # csv_str = ""
        # for i, name in enumerate(self.labels):
        #     csv_str += self.normalize_name(name)+ ',' + str(i) + '\n'
        #
        #  # training samples - save samples to csv file
        # csv_out_filename = os.path.join('./data', self.base_filename + "_ordered.csv")
        # with open(csv_out_filename, 'w', encoding='utf-8') as text_file:
        #     text_file.write(csv_str)

        # make a copy of the labels preprocessed (lower case, remove accents and more)
        self.preprocessed_labels = [self.normalize_name(label) for label in self.labels]

        self.basic_functions = basic_functions
        self.expanding_functions = expanding_functions

        # create training samples
        self.training_set_list = self._process_labels()
        self._remove_duplicate_samples()

        self.labels_weight = self._get_weight_labels()

    @staticmethod
    def normalize_name(s):
        # lower case and accents removed
        s = unidecode.unidecode(s).lower()

        # replace apostrophe and dash by space
        s = s.replace("-", ' ')
        s = s.replace("'", ' ')

        return s

    def save(self, output_dir, text_column, label_column):
        """
        save 2 files:
          output_dir/{base_filename}_training_set.csv
          output_dir/{base_filename}_training_labels.pickle
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # insert csv header
        csv_str = f"{text_column},{label_column}\n" + self.training_set_list

        # training samples - save samples to csv file
        training_set_filename = os.path.join(output_dir, self.base_filename + "_training_set.csv")
        with open(training_set_filename, 'w', encoding='utf-8') as text_file:
            text_file.write(csv_str)

        # labels - save labels, label to indexes and labels weight
        obj_to_save = [
            self.labels,
            self.label2idx,
            self.labels_weight,
        ]
        labels_out_filename = os.path.join(output_dir, self.base_filename + "_training_labels.pickle")
        pickle.dump(obj_to_save, open(labels_out_filename, "wb"))

        return training_set_filename, labels_out_filename

    @staticmethod
    def get_entity_list(input_filename):
        entity_list = None
        if os.path.isfile(input_filename):
            df = pd.read_csv(input_filename, sep=',', header=None)
            entity_list = list(df[0])

        return entity_list

    def _process_labels(self):
        result_list = []

        function_list = self.basic_functions + self.expanding_functions

        if self.labels:
            for entity_name in self.labels:
                # remove leading and trailing spaces
                entity_name = entity_name.strip()
                # make an unaccented lowercase version of the entity_name
                unaccented_entity_name = self.normalize_name(entity_name)

                # add the unaccented version as the first sample
                entity_mention_list = [unaccented_entity_name]

                # add additional sample by passing the unaccented version through the various functions
                if function_list:
                    # get a new entity mention for this entity name using each transform functions
                    for fnc in function_list:
                        entity_mentions = eval(f'self.{fnc}("{unaccented_entity_name}")')

                        for mention in entity_mentions:
                            # do not add duplicate entries
                            if mention not in entity_mention_list:
                                # do not add an entry that is equals to a label
                                if mention not in self.preprocessed_labels:
                                    entity_mention_list.append(mention)

                result_list.append({entity_name: entity_mention_list})

        # convert the list in one sample per line string
        samples = ""
        for entity in result_list:
            for entity_name, entity_mention_list in entity.items():
                for entity_mention in entity_mention_list:
                    # samples += f"{entity_mention},{entity_name}\n"
                    samples += f"{entity_mention},{self.label2idx[entity_name]}\n"

        return samples.rstrip()

    def _remove_duplicate_samples(self):
        """ make sure that no two mentions point to different entity names, like:
               place, Place-Saint-Henri
               place, Place-d'Armes
        """
        df = pd.read_csv(StringIO(self.training_set_list), sep=',', header=None)

        # find duplicate
        dup = df[df.duplicated([0])]
        dup_list = dup[0].unique()

        # remove all rows that is part of the duplicate list
        df = df[~df[0].isin(dup_list)]

        # save to csv string
        new_csv_str = io.StringIO()
        df.to_csv(new_csv_str, header=False, index=False)

        self.training_set_list = new_csv_str.getvalue().rstrip()

    def _get_weight_labels(self):
        """
        Return weight for each classes to get ride of the classes imbalance.
        A list of float [0, 1], one for each classes, 1.0 to the smallest classes.

        Intended to be passed to PyTorch nn.CrossEntropyLoss(weight).
        """
        csv_str = "EntityMention,EntityName\n" + self.training_set_list
        df = pd.read_csv(StringIO(csv_str), sep=',')

        sample_per_classes_count = df.groupby('EntityName').count()['EntityMention']
        self.smallest_class_nb_sample = sample_per_classes_count.min()

        return (self.smallest_class_nb_sample / sample_per_classes_count.values).tolist()

    def expand(self, name, function_list):
        result_list = []

        # add additional samples by passing the it through the various functions.
        # do not add an entry that is equals to a label
        if name and name not in self.preprocessed_labels:
            # add the unaccented version as the first sample
            result_list = [name]

            # get a new version for this label using each transform functions
            for fnc in function_list:
                label_variations = eval(f'self.{fnc}("{name}")')

                for label_variation in label_variations:
                    # do not add duplicate entries
                    if label_variation not in result_list:
                        result_list.append(label_variation)

        return result_list

    def do_word_split(self, s, word_split_fnc):
        result = word_split_fnc(s, ' ')
        if not result:
            result = word_split_fnc(s, '-')

        # add additional samples by passing the it through the various functions.
        # result_list = self.expand(result, self.basic_functions + ["expand_saint"])
        result_list = self.expand(result, self.basic_functions)

        return result_list if result_list != [] and len(result_list[0]) > 2 else [s]

    def dash_space(self, s):
        """ replace all dash by space """
        return [s.replace('-', ' ')]

    def apostrophe_space(self, s):
        """ replace all apostrophe by space """
        return [s.replace("'", ' ')]

    def remove_dash(self, s):
        """ replace all dash by space """
        return [s.replace('-', '')]

    def space_dash(self, s):
        """ replace all space by dash """
        return [s.replace(' ', '-')]

    def remove_double_letter(self, s):
        """ remove the first double letter from the given string """
        match = re.search(r"([a-z])\1", s)
        if match:
            s = s.replace(match.group(1)+match.group(1), match.group(1), 1)
        return [s]

    def remove_random_letter_all(self, s):
        """ remove a random letter from the given string, do every chars """
        r = list(range(len(s) - 1))
        random.shuffle(r)
        result = []

        for r in r[:self.max_mixup]:
            result.extend(self.remove_random_letter(s, r))
        return result

    def remove_random_letter(self, s, r=None):
        """ remove a random letter from the given string. """
        if r is None:
            r = random.randint(0, len(s) - 1)
        ss = [s[:r] + s[r + 1:]]
        return ss if len(ss) > 2 else [s]

    def invert_two_letters_all(self, s):
        """ remove a random letter from the given string, do every chars """
        r = list(range(len(s)-1))
        random.shuffle(r)
        result = []

        for r in r[:self.max_mixup]:
            result.extend(self.invert_two_letters(s, r))
        return result

    def invert_two_letters(self, s, r=None):
        """ remove a random letter from the given string. """
        if r is None:
            r = random.randint(0, len(s)-2)
        return [s[:r] + s[r+1] + s[r] + s[r+2:]]

    def expand_de(self, s):
        """ expand '-de-' like in Université-de-Montréal --> Université-Montréal """
        if s.find('-de-') != -1 or s.find(' de ') != -1:
            return [
                s.replace(' de ', ' '),
            ]
        return [s]

    def expand_saint(self, s):
        new_list = None

        """ change 'saint-' into all its variation: sainte- ste- st- """
        if s.find('sainte-') != -1 or s.find('sainte ') != -1:
            new_list = [
                s.replace('sainte ', 'saint ', 1),
                s.replace('sainte ', 'ste ', 1),
                s.replace('sainte ', 'st ', 1),
            ]
        else:
            if s.find('saint-') != -1 or s.find('saint ') != -1:
                new_list = [
                    s.replace('saint ', 'sainte ', 1),
                    s.replace('saint ', 'ste ', 1),
                    s.replace('saint ', 'st ', 1),
                ]

        if new_list:
            return [n for new_name in new_list for n in self.expand(new_name, self.basic_functions)]

        return [s]

    def saint_next_word(self, s):
        """ Place-Saint-Henri --> Saint-Henri """
        def word_split(s, sep):
            words = s.split(sep)
            if len(words) > 2:
                for i, w in enumerate(words):
                    if w.startswith("saint"):
                        return sep.join([w, words[i+1]])
            return None

        return self.do_word_split(s, word_split)

    def remove_first_word(self, s):
        """ Square-Victoria-OACI --> Victoria-OACI """
        def word_split(s, sep):
            words = s.split(sep)
            if len(words) > 1:
                return sep.join([w for w in words[1:]])
            return None

        return self.do_word_split(s, word_split)

    def remove_last_word(self, s):
        """ Square-Victoria-OACI --> Square-Victoria """
        def word_split(s, sep):
            words = s.split(sep)
            if len(words) > 1:
                return sep.join([w for w in words[:-1]])
            return None

        return self.do_word_split(s, word_split)

    def only_first_word(self, s):
        """ Square-Victoria-OACI --> Square """
        def word_split(s, sep):
            words = s.split(sep)
            if len(words) > 1:
                return words[0]
            return None

        return self.do_word_split(s, word_split)

    def only_last_word(self, s):
        """ Square-Victoria-OACI --> OACI """
        def word_split(s, sep):
            words = s.split(sep)
            if len(words) > 1:
                return words[-1]
            return None

        return self.do_word_split(s, word_split)

    def only_first_and_last(self, s):
        """ Square-Victoria-OACI --> Square-OACI """
        def word_split(s, sep):
            words = s.split(sep)
            if len(words) > 2:
                return sep.join([words[0], words[-1]])
            return None

        return self.do_word_split(s, word_split)

    def random_underscore_all(self, s):
        """ jarry -> jar_y """
        ran = list(range(len(s)))
        random.shuffle(ran)
        result = []

        for r in ran[:self.max_mixup]:
            ss = s[:r] + '_' + s[r+1:]
            result.extend([ss])
        return result

    def add_random_letter_all(self, s):
        """ peel -> peekl """
        ran = list(range(len(s) - 1))
        random.shuffle(ran)
        result = []

        for r in ran[:self.max_mixup]:
            result.extend(self.add_random_letter(s, r))
        return result

    def add_random_letter(self, s, r=None):
        """ peel -> peekl """
        if r is None:
            r = random.randint(0, len(s) - 1)

        slist = list(s)
        bad_stroke = self.bad_stroke_list.get(slist[r])
        bad_stroke = bad_stroke if bad_stroke else 'z'

        return [s[:r] + bad_stroke + s[r:]]


def get_training_word_list(data_filename, encoding='utf-8', header=1):
    texts = []

    if data_filename:
        # read csv file using pandas dataframe
        # df = pd.read_csv(data_filename, usecols=[text_column, label_column], encoding=encoding)
        df = pd.read_csv(data_filename, encoding=encoding, header=header)
        texts  = df[df.columns[0]].tolist()

    return texts


def generate_training_set(args):
    print("--- generating training data set ---")

    generator = DatasetGenerator(args.source_data_path, basic_functions, expanding_functions)

    if generator.training_set_list and (args.verbose == "True"):
        print(f"Number of classes = {len(generator.labels)}")
        print(f"Number of samples in generated training set = {len(generator.training_set_list)}")
        print(f"Smallest samples count for a class = {generator.smallest_class_nb_sample}")

    # save 2 files:
    #   ./data/{basename}_training_set.csv
    #   ./data/{basename}_training_labels.pickle
    training_set_filename, labels_filename = generator.save(args.output_path, args.text_column, args.label_column)

    return training_set_filename, labels_filename, generator.base_filename


def create_embedding(args, training_list):
    ngram = NgramHashing(args.embedding_ngram_size, corpus_text_list=training_list)

    # train the embedding with all samples except those that contains '_'
    # training_token_list = [t for w in training_list if '_' not in w for t in ngram.ngram(NgramHashing.ascii_trim_lowercase(w))]
    training_token_list = [t for w in training_list if '_' not in w for t in
                           ngram.ngram(DatasetGenerator.normalize_name(w))]

    embedding = NgramEmbedding(ngram=ngram)
    embedding.train_ngram(training_token_list,
                          args.embedding_epochs,
                          embedding_dim=args.embedding_dim,
                          hidden_size=args.embedding_hidden_layer_size,
                          lr=args.embedding_learning_rate,
                          verbose=(args.verbose == "True"))
    return embedding


if __name__ == "__main__":
    basic_functions = [
        "random_underscore_all",

        # "dash_space",
        # "apostrophe_space",
        # "space_dash",
        # "remove_dash",
        # "remove_double_letter",
        # "random_single_bad_stroke_all",
        # "invert_two_letters_all",
        # "remove_random_letter_all",
        # "add_random_letter_all",
    ]

    expanding_functions = [
        "saint_next_word",
        # "expand_saint",
        "expand_de",

        "remove_first_word",
        "remove_last_word",

        "only_first_word",
        "only_last_word",
        "only_first_and_last",
    ]

    parser = argparse.ArgumentParser('Training dataset generator')

    parser.add_argument('--source_data_path', type=str, default='./metro.csv')
    parser.add_argument('--output_path', type=str, default='./data')

    parser.add_argument('--text_column', type=str, default='EntityMention')
    parser.add_argument('--label_column', type=str, default='EntityName')

    parser.add_argument('--embedding_dim', type=int, default=32)
    parser.add_argument('--embedding_hidden_layer_size', type=int, default=128)
    parser.add_argument('--embedding_ngram_size', type=int, default=2)
    parser.add_argument('--embedding_learning_rate', type=float, default=0.0001)
    parser.add_argument('--embedding_epochs', type=int, default=15)

    parser.add_argument('--verbose', type=str, default="True")

    args = parser.parse_args()

    # -------------------------------------

    # training set generation
    training_set_filename, labels_filename, base_filename = generate_training_set(args)

    # create embedding
    training_list = get_training_word_list(training_set_filename)
    embedding = create_embedding(args, training_list)

    embedding_filename = os.path.join(args.output_path, base_filename + "_embedding.pth")
    vocab_filename = os.path.join(args.output_path, base_filename + "_vocab.pickle")
    embedding.save(embedding_filename, vocab_filename)
