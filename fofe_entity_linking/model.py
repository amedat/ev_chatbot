import torch
import torch.nn as nn
import torch.nn.functional as F


class FofeNNModel(nn.Module):

    def __init__(self, embedding_dim, hidden_size, dropoutrate, number_of_classes):
        super(FofeNNModel, self).__init__()

        self.embedding_dim = embedding_dim
        self.hidden_size = hidden_size

        self.fc1 = nn.Linear(in_features=self.embedding_dim, out_features=self.hidden_size)
        self.fc2 = nn.Linear(in_features=self.hidden_size, out_features=number_of_classes)

        #self.bn1 = nn.BatchNorm1d(hidden_size)
        self.dropout = nn.Dropout(p=dropoutrate)

    def forward(self, input):
        x = input
        x = F.relu(self.fc1(x))
        # x = self.bn1(F.relu(self.fc1(x)))
        x = self.dropout(x)
        output = self.fc2(x)
        log_probs = F.log_softmax(output, dim=1)    # F.log_softmax() ??? why not just a F.softmax()
        return log_probs
