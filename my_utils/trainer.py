from torch.optim.lr_scheduler import _LRScheduler
import torch.optim as optim
from torch import cuda, isinf, no_grad
import torch.nn as nn


class WarmUpLR(_LRScheduler):
    def __init__(self, optimizer, total_iters, last_epoch=-1):
        self.total_iters = total_iters
        super().__init__(optimizer, last_epoch)

    def get_lr(self):
        return [base_lr * self.last_epoch / (self.total_iters + 1e-8) for base_lr in self.base_lrs]


class Trainer:
    device = 'cuda' if cuda.is_available() else 'cpu'

    def __init__(self, model, loader, lr, warmup_epochs=5):
        self.model = model
        self.optimizer = optim.SGD(model.parameters(), lr=lr)
        self.warmup_scheduler = WarmUpLR(self.optimizer, len(loader) * warmup_epochs)
        self.model.to(self.device)
        # loss
        self.train_loss_list, self.valid_loss_list, self.test_loss_list = [], [], []
        # loss function
        self.cross_entropy = nn.CrossEntropyLoss()

    def iteration(self, loader, lr_warmup, msg=''):
        batch_loss = 0
        for batch_idx, (inputs, targets) in enumerate(loader):
            if lr_warmup:
                self.warmup_scheduler.step()
            inputs, targets = inputs.to(Trainer.device), targets.to(Trainer.device)
            outputs = self.model(inputs)
            self.optimizer.zero_grad()
            loss = self.cross_entropy(outputs, targets)
            if isinf(loss) and msg == 'training':
                print('[Error] nan loss, stop {}.'.format(msg))
                exit(1)
            loss.backward()
            self.optimizer.step()
            batch_loss = batch_loss + loss.item()
        return batch_loss / len(loader)

    def train(self, loader, lr_warmup):
        self.model.train()
        train_loss = self.iteration(loader, lr_warmup, msg='training')
        self.train_loss_list.append(train_loss)

    def valid(self, loader):
        self.model.eval()
        valid_loss = self.iteration(loader, lr_warmup=False, msg='validation')
        self.valid_loss_list.append(valid_loss)

    def test(self, loader):
        self.model.eval()
        test_loss = self.iteration(loader, lr_warmup=False, msg='test')
        self.test_loss_list.append(test_loss)

