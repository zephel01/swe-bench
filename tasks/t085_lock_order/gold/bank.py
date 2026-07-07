import threading


class Account:
    def __init__(self, acct_id, balance):
        self.id = acct_id
        self.balance = balance
        self.lock = threading.Lock()


class Bank:
    def transfer(self, src, dst, amount):
        first, second = (src, dst) if src.id <= dst.id else (dst, src)
        with first.lock, second.lock:
            if src.balance < amount:
                return False
            src.balance -= amount
            dst.balance += amount
            return True
