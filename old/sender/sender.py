#!/usr/bin/env python3

import json
import secrets
from web3 import Web3


class FairdexSender:
    def __init__(self):

        with open('sender.conf', 'r') as conf_file:
            conf = [line.strip().split('=')[1] for line in conf_file.readlines()]

        infura_url = conf[0]
        self.sender = conf[1]
        self.sender_private = conf[2]
        contract_address = conf[3]
        self.gas_price = conf[4]
        desc_depth = int(conf[5])
        subkey_depth = 14
         
        self.web3 = Web3(Web3.WebsocketProvider(infura_url))
        with open('fairdex.abi', 'r') as abifile:
            abi = json.load(abifile)

        checksum_address = self.web3.toChecksumAddress(contract_address)
        self.contract = self.web3.eth.contract(address=checksum_address, abi=abi)

        self.master_key = secrets.token_bytes(32)
        self.wrong_key = secrets.token_bytes(32)

        subkeys = []
        number_of_subkeys = 2 ** subkey_depth
        for i in range(number_of_subkeys):
            sk = Web3.solidityKeccak(['bytes32', 'uint256'], [self.master_key, i])
            subkeys.append(sk)

        number_of_random_indices = 2 ** desc_depth
        secure_random = secrets.SystemRandom()
        random_indices = secure_random.sample(range(number_of_subkeys), number_of_random_indices)

        with open('offchain.txt', 'w') as offline_message:
            for r in random_indices:
                offline_message.write(f'{Web3.toHex(subkeys[r])} {r}\n')

    def publish_master_key(self):
        nonce = self.web3.eth.getTransactionCount(self.sender)
        transaction = self.contract.functions.PublishMasterKey(self.master_key).buildTransaction({
            'gas': 3000000,
            'gasPrice': self.web3.toWei(self.gas_price, 'gwei'),
            'from': self.sender,
            'nonce': nonce,
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction, private_key=self.sender_private)
        tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        return tx_hash

    def publish_wrong_key(self):
        nonce = self.web3.eth.getTransactionCount(self.sender)
        transaction = self.contract.functions.PublishMasterKey(self.wrong_key).buildTransaction({
            'gas': 3000000,
            'gasPrice': self.web3.toWei(self.gas_price, 'gwei'),
            'from': self.sender,
            'nonce': nonce,
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction, private_key=self.sender_private)
        tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        return tx_hash

    def transfer_to_seller(self):
        nonce = self.web3.eth.getTransactionCount(self.sender)
        transaction = self.contract.functions.TransferToSeller().buildTransaction({
            'gas': 3000000,
            'gasPrice': self.web3.toWei(self.gas_price, 'gwei'),
            'from': self.sender,
            'nonce': nonce,
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction, private_key=self.sender_private)
        tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        return tx_hash

    def get_contract_state(self):
        try:
            state = self.contract.functions.state().call()
            if state == 0:
                return 'Created'
            elif state == 1:
                return 'Paid'
            elif state == 2:
                return 'Published'
        except:
            return 'Inactive'

    def get_balance(self):
        balance_wei = self.web3.eth.getBalance(self.sender)
        balance_eth = self.web3.fromWei(balance_wei, 'ether')
        return balance_eth


def execute(_fairdex_sender, _operation, _state):
    state = _fairdex_sender.get_contract_state()
    if state == _state:
        operation = getattr(_fairdex_sender, _operation)
        txhash = operation()
        print(f'Message sent to blockchain.\nTxn: {Web3.toHex(txhash)}\n')
    else:
        print(f'This operation can be called only if the state is {_state}.\n')


def main():
    sender = FairdexSender()

    print('FairDEx: Practical Fair Exchange of Digital Goods')
    print('Client Application for Sender v1.0')
    print()
    print(f'Contract:   {sender.contract.address}')
    print(f'State:      {sender.get_contract_state()}')
    print(f'Master Key: {Web3.toHex(sender.master_key)}')
    print()
    print('Commands:')
    print(' [1] Publish Master Key                 [2] Transfer to Seller')
    print(' [3] Publish a Wrong Key                [4] Print State')
    print(' [5] Print Balance                      [0] Quit')
    print()

    while True:
        choice = int(input('Enter your choice: '))
        if choice == 1:
            execute(sender, 'publish_master_key', 'Paid')
        elif choice == 2:
            execute(sender, 'transfer_to_seller', 'Published')
        elif choice == 3:
            execute(sender, 'publish_wrong_key', 'Paid')
        elif choice == 4:
            print(f'State: {sender.get_contract_state()}\n')
        elif choice == 5:
            print(f'Balance: {sender.get_balance():.5} ETH\n')
        elif choice == 0:
            print('Quitting.\n')
            break
        else:
            print('Invalid choice. Valid chocices are 0 to 5.\n')


if __name__ == '__main__':
    main()
