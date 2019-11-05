import os
import shutil
import argparse
import pickle

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd

from torch.utils.data import DataLoader
#from tensorboardX import SummaryWriter
from sklearn import metrics
from tqdm import tqdm

from .model import FofeNNModel
from .dataset import FofeDataset
from .embedding import NgramEmbedding


def train(model, training_generator, optimizer, criterion):
    model.train()

    losses = []
    accuraries = []
    f1_scores = []
    num_iter_per_epoch = len(training_generator)

    progress_bar = tqdm(enumerate(training_generator), total=num_iter_per_epoch)

    for iter, batch in progress_bar:
        features, labels = batch
        if torch.cuda.is_available():
            features = features.cuda()
            labels = labels.cuda()

        optimizer.zero_grad()
        predictions = model(features)
        loss = criterion(predictions, labels)
        loss.backward()
        optimizer.step()

        training_metrics = get_evaluation(labels.cpu().numpy(),
                                          predictions.cpu().detach().numpy(),
                                          ["accuracy", "f1"])

        losses.append(loss.item())
        accuraries.append(training_metrics["accuracy"])
        f1_scores.append(training_metrics['f1'])

    return np.mean(losses), np.mean(accuraries), np.mean(f1_scores)


def get_classes(y_true, y_prob, bad_pred_ids):
    y_pred = np.argmax(y_prob, -1)
    return [[y_pred[idx], y_true[idx], idx] for idx in bad_pred_ids]


def get_evaluation(y_true, y_prob, list_metrics):
    y_pred = np.argmax(y_prob, -1)
    output = {}
    if 'accuracy' in list_metrics:
        output['accuracy'] = metrics.accuracy_score(y_true, y_pred)

    if 'f1' in list_metrics:
        output['f1'] = metrics.f1_score(y_true, y_pred, average='macro')

    # compute the indexes of bad predicted labels
    if 'bad_pred_indexes' in list_metrics:
        output['bad_pred_indexes'] = (np.array(y_true) - np.array(y_pred)).nonzero()[0].tolist()

    return output


def print_bad_predictions(bad_predictions, sample_list=None):
    print('BAD PREDICTIONS')
    print('---------------')
    print('truth\t\tpred\n')
    for pred_idx, true_idx, idx in bad_predictions:
        if sample_list:
            print(f"{sample_list[idx]} ({labels[true_idx]})  -->  {labels[pred_idx]}")
        else:
            print(f"{labels[true_idx]}\t-->\t{labels[pred_idx]}")


def evaluate(model, validation_generator, criterion, collect_bad_predictions=False):
    model.eval()

    losses = []
    accuraries = []
    f1_scores = []
    bad_predictions = []
    num_iter_per_epoch = len(validation_generator)

    for iter, batch in tqdm(enumerate(validation_generator), total=num_iter_per_epoch):
        features, labels = batch
        if torch.cuda.is_available():
            features = features.cuda()
            labels = labels.cuda()

        with torch.no_grad():
            predictions = model(features)

        loss = criterion(predictions, labels)

        labels_numpy = labels.cpu().numpy()
        predictions_numpy = predictions.cpu().detach().numpy()

        metrics_list = ["accuracy", "f1", "bad_pred_indexes"] if collect_bad_predictions else ["accuracy", "f1"]
        valid_metrics = get_evaluation(labels_numpy, predictions_numpy, metrics_list)

        accuracy = valid_metrics['accuracy']

        losses.append(loss.item())
        accuraries.append(accuracy)
        f1_scores.append(valid_metrics['f1'])

        if collect_bad_predictions:
            bad_predictions += get_classes(labels_numpy, predictions_numpy, valid_metrics['bad_pred_indexes'])

    return np.mean(losses), np.mean(accuraries), np.mean(f1_scores), bad_predictions


def run_testset(args, model, embedding=None):
    testset = FofeDataset(args.data_testset_path,
                          args.text_column, args.label_column, args.encoding,
                          args.number_of_classes,
                          embedding=embedding,
                          forgetting_factor=args.fofe_forgetting_factor,
                          ngram=args.ngram_size,
                          max_tokens=args.max_length)

    test_generator = DataLoader(testset, batch_size=256, shuffle=False, num_workers=args.workers)

    if torch.cuda.is_available():
        model.cuda()

    criterion = nn.NLLLoss()

    test_loss, test_accuracy, test_f1, bad_predictions = evaluate(model, test_generator, criterion,
                                                                  collect_bad_predictions=True)

    print('\ntest_loss: {:.4f} \ttest_acc: {:.4f} \ttest_f1: {:.4f}'.format(test_loss, test_accuracy, test_f1))
    print("=" * 55)

    return bad_predictions


def run(args, embedding=None, labels_weight=None):
    # log folder
    if not os.path.exists(args.log_path):
        os.makedirs(args.log_path)

    # model output folder
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    model_output_filename = os.path.join(args.output, args.model_name + ".pth")

    log_name = args.log_path + args.model_name
    print(log_name)
    # writer = SummaryWriter(log_name)
    writer = None

    batch_size = args.batch_size

    training_params   = {"batch_size": batch_size, "shuffle": True,  "num_workers": args.workers}
    validation_params = {"batch_size": batch_size, "shuffle": False, "num_workers": args.workers}

    # DATASET
    full_dataset = FofeDataset(args.data_path,
                               args.text_column, args.label_column, args.encoding,
                               args.number_of_classes,
                               embedding=embedding,
                               forgetting_factor=args.fofe_forgetting_factor,
                               ngram=args.ngram_size,
                               max_tokens=args.max_length)

    train_size = int(args.validation_split * len(full_dataset))
    validation_size = len(full_dataset) - train_size

    training_set, validation_set = torch.utils.data.random_split(full_dataset, [train_size, validation_size])

    # DATASET LOADER
    training_generator = DataLoader(training_set, **training_params)
    validation_generator = DataLoader(validation_set, **validation_params)

    if labels_weight:
        labels_weight = torch.tensor(np.array(labels_weight), dtype=torch.float32)

    # MODEL
    model = FofeNNModel(full_dataset.embedding_dim,
                        hidden_size=args.hidden_layer_size,
                        dropoutrate=args.dropout_rate,
                        number_of_classes=args.number_of_classes)

    if torch.cuda.is_available():
        model.cuda()
        labels_weight = labels_weight.cuda()

    # loss taking care of Class Imbalance if specified
    # criterion = nn.CrossEntropyLoss(weight=labels_weight)
    criterion = nn.NLLLoss(weight=labels_weight)

    if args.optimizer == 'sgd':
        optimizer = torch.optim.SGD(model.parameters(), lr=args.learning_rate, momentum=0.9)

    elif args.optimizer == 'adam':
        optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    model_saved = False
    collect_bad_predictions = False
    best_loss = 1e10
    best_epoch = 0

    # TRAINING LOOP
    for epoch in range(args.epochs):
        if epoch == args.epochs -1:
            collect_bad_predictions = True

        train_loss, train_accuracy, train_f1 = train(model, training_generator, optimizer, criterion)

        val_loss, val_accuracy, val_f1, bad_predictions = evaluate(model, validation_generator, criterion,
                                                                   collect_bad_predictions=collect_bad_predictions)

        print('\n[Epoch: {} / {}]\ttrain_loss: {:.4f} \ttrain_acc: {:.4f} \ttrain_f1: {:.4f} \tval_loss: {:.4f} \tval_acc: {:.4f} \tval_f1: {:.4f}'.
              format(epoch + 1, args.epochs, train_loss, train_accuracy, train_f1, val_loss, val_accuracy, val_f1))
        print("=" * 50)

        if writer:
            writer.add_scalar('Train/Loss', train_loss, epoch)
            writer.add_scalar('Train/Accuracy', train_accuracy, epoch)
            writer.add_scalar('Train/f1', train_f1, epoch)

            writer.add_scalar('Valid/Loss', val_loss, epoch)
            writer.add_scalar('Valid/Accuracy', val_accuracy, epoch)
            writer.add_scalar('Valid/f1', val_f1, epoch)

        # learning rate scheduling
        if args.schedule != 0:
            # if args.optimizer == 'sgd' and epoch % args.schedule == 0 and epoch > 0:
            if epoch % args.schedule == 0 and epoch > 0:
                current_lr = optimizer.state_dict()['param_groups'][0]['lr']
                # current_lr /= 2
                current_lr *= 0.20
                print('Decreasing learning rate to {0}'.format(current_lr))
                for param_group in optimizer.param_groups:
                    param_group['lr'] = current_lr

        if val_loss < best_loss:
            best_loss = val_loss
            best_epoch = epoch
            if args.checkpoint == 1 and val_accuracy > 0.97:
                torch.save(model.state_dict(), model_output_filename)
                collect_bad_predictions = True
                model_saved = True
        else:
            collect_bad_predictions = False

        if bad_predictions:
            print_bad_predictions(bad_predictions)

        # early stopping
        if epoch - best_epoch > args.patience > 0:
            print("Stop training at epoch {}. The lowest loss achieved is {} at epoch {}".format(epoch, val_loss, best_epoch))
            break

    # save last epoch, if not done yet
    if not model_saved:
        torch.save(model.state_dict(), model_output_filename)

    if writer:
        writer.close()

    return bad_predictions, model


if __name__ == "__main__":
    parser = argparse.ArgumentParser('FOFE-based NN for text classification')

    parser.add_argument('--data_path', type=str, default='./data/metro_training_set.csv')
    parser.add_argument('--data_testset_path', type=str, default='./data/metro_test_set.csv')

    parser.add_argument('--label_weight_path', type=str, default='./data/metro_training_labels.pickle')
    parser.add_argument('--vocab_path', type=str, default='./data/metro_vocab.pickle')
    parser.add_argument('--embedding_path', type=str, default='./data/metro_embedding.pth')

    parser.add_argument('--validation_split', type=float, default=0.95)
    parser.add_argument('--label_column', type=str, default='EntityName')
    parser.add_argument('--text_column', type=str, default='EntityMention')
    parser.add_argument('--encoding', type=str, default='utf-8')

    parser.add_argument('--max_length', type=int, default=50)
    parser.add_argument('--number_of_classes', type=int, default=68)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--optimizer', type=str, choices=['adam', 'sgd'], default='adam')
    parser.add_argument('--learning_rate', type=float, default=0.0005)
    parser.add_argument('--schedule', type=int, default=10)
    parser.add_argument('--patience', type=int, default=50)
    parser.add_argument('--checkpoint', type=int, choices=[0, 1], default=1)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--log_path', type=str, default='./logs/')
    parser.add_argument('--output', type=str, default='./models/')
    parser.add_argument('--model_name', type=str, default='')

    parser.add_argument('--fofe_forgetting_factor', type=float, default=0.95)
    parser.add_argument('--ngram_size', type=int, default=2)
    parser.add_argument('--dropout_rate', type=float, default=0.50)
    parser.add_argument('--hidden_layer_size', type=int, default=1536)

    # TODO - 2 hidden layers with different size [1024x512]
    # TODO - experimement with various forgetting_factor

    print(f"torch.cuda.is_available() = {torch.cuda.is_available()}")

    torch.backends.cudnn.deterministic = True
    torch.manual_seed(999)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(999)

    args = parser.parse_args()

    # load labels weight to balance the training data
    labels, label2idx, labels_weight = pickle.load(open(args.label_weight_path, "rb"))

    # load embedding
    embedding = NgramEmbedding(embedding_filename=args.embedding_path,
                               vocab_filename=args.vocab_path)

    # train the model
    bad_predictions, model = run(args, embedding, labels_weight)

    if args.data_testset_path:
        # test the model
        bad_predictions = run_testset(args, model, embedding)

        # get samples list
        df = pd.read_csv(args.data_testset_path, usecols=[args.text_column, args.label_column], encoding=args.encoding)
        test_sample_list  = df[args.text_column].tolist()

        print('----------------------------------------------------------')
        print(' T E S T')
        print('----------------------------------------------------------')
        # print_bad_predictions(bad_predictions)
        print_bad_predictions(bad_predictions, test_sample_list)
