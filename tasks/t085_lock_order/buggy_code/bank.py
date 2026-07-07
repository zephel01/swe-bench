import threading


class Account:
    def __init__(self, acct_id, balance):
        self.id = acct_id
        self.balance = balance
        self.lock = threading.Lock()


class Bank:
    def transfer(self, src, dst, amount):
        with src.lock:
            with dst.lock:
                if src.balance < amount:
                    return False
                src.balance -= amount
                dst.balance += amount
                return True
