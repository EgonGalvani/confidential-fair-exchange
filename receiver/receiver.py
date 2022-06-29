#!/usr/bin/env python3

import json
from web3 import Web3

class FairdexReceiver:
    def __init__(self):

        with open('receiver.conf', 'r') as conf_file:
            conf = [line.strip().split('=')[1] for line in conf_file.readlines()]

        infura_url = conf[0]
        self.receiver = conf[1]
        self.receiver_private = conf[2]
        contract_address = conf[3]
        self.gas_price = conf[4]
        self.desc_depth = int(conf[5])

        self.web3 = Web3(Web3.WebsocketProvider(infura_url))

        with open('fairdex.abi', 'r') as abifile:
            abi = json.load(abifile)

        checksum_address = self.web3.toChecksumAddress(contract_address)
        self.contract = self.web3.eth.contract(address=checksum_address, abi=abi)

        self.sampled_keys = []
        self.sampled_indices = []
        self.nodes = []
        number_of_sampled_keys = 2 ** self.desc_depth

        with open('offchain.txt', 'r') as offline_message:
            lines = [line.strip() for line in offline_message.readlines()]

            for i in range(number_of_sampled_keys):
                sk, r = lines[i].split()
                self.sampled_keys.append(sk)
                self.sampled_indices.append(int(r))
                nd = Web3.solidityKeccak(['bytes32', 'uint256'], [sk, int(r)])
                self.nodes.append(nd)

        self.description = self.calculate_merkle_root(self.nodes)
        self.m_proof = self.calculate_merkle_proof()

    def calculate_merkle_root(self, arr):
        length = len(arr)

        if length == 2:
            result = Web3.solidityKeccak(['bytes32', 'bytes32'], [arr[0], arr[1]])
        else:
            left_arr = arr[:length // 2]
            right_arr = arr[length // 2:]
            left_hash = self.calculate_merkle_root(left_arr)
            right_hash = self.calculate_merkle_root(right_arr)
            result = Web3.solidityKeccak(['bytes32', 'bytes32'], [left_hash, right_hash])

        return result

    def calculate_merkle_proof(self):
        result = [self.nodes[1]]
        start_pos = 2

        for i in range(1, self.desc_depth):
            chunk_size = 2 ** i
            end_pos = start_pos + chunk_size
            arr = self.nodes[start_pos:end_pos]
            result.append(self.calculate_merkle_root(arr))
            start_pos = end_pos

        return result

    def pay_with_description(self):
        nonce = self.web3.eth.getTransactionCount(self.receiver)
        transaction = self.contract.functions.PayWithDescription(self.description).buildTransaction({
            'gas': 3000000,
            'gasPrice': self.web3.toWei(self.gas_price, 'gwei'),
            'from': self.receiver,
            'nonce': nonce,
            'value': self.web3.toWei(100, 'finney')  # 0.1 ether
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction, private_key=self.receiver_private)
        tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        return tx_hash

    def raise_objection(self):
        nonce = self.web3.eth.getTransactionCount(self.receiver)
        transaction = self.contract.functions.RaiseObjection(self.sampled_indices[0], self.sampled_keys[0],
                                                             self.m_proof).buildTransaction({
            'gas': 3000000,
            'gasPrice': self.web3.toWei(self.gas_price, 'gwei'),
            'from': self.receiver,
            'nonce': nonce,
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction, private_key=self.receiver_private)
        tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        return tx_hash

    def refund_to_buyer(self):
        nonce = self.web3.eth.getTransactionCount(self.receiver)
        transaction = self.contract.functions.RefundToBuyer().buildTransaction({
            'gas': 3000000,
            'gasPrice': self.web3.toWei(self.gas_price, 'gwei'),
            'from': self.receiver,
            'nonce': nonce
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction, private_key=self.receiver_private)
        tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        return tx_hash

    def get_master_key(self):
        state = self.get_contract_state()
        if state == 'Published':
            master_key = self.contract.functions.masterKey().call()
            return Web3.toHex(master_key)
        else:
            return 'n/a'

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
        balance_wei = self.web3.eth.getBalance(self.receiver)
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
    receiver = FairdexReceiver()

    print('FairDEx: Practical Fair Exchange of Digital Goods')
    print('Client Application for Receiver v1.0')
    print()
    print(f'Contract Address: {receiver.contract.address}')
    print(f'State: {receiver.get_contract_state()}')
    print()
    print('Commands:')
    print(' [1] Pay with Description               [2] Get Master Key from Contract')
    print(' [3] Raise Objection                    [4] Refund to Buyer')
    print(' [5] Print State                        [6] Print Balance')
    print(' [0] Quit')
    print()

    while True:
        choice = int(input('Enter your choice: '))
        if choice == 1:
            execute(receiver, 'pay_with_description', 'Created')
        elif choice == 2:
            print(f'Master Key: {receiver.get_master_key()}\n')
        elif choice == 3:
            execute(receiver, 'raise_objection', 'Published')
        elif choice == 4:
            execute(receiver, 'refund_to_buyer', 'Paid')
        elif choice == 5:
            print(f'State: {receiver.get_contract_state()}\n')
        elif choice == 6:
            print(f'Balance: {receiver.get_balance():.5} ETH\n')
        elif choice == 0:
            print('Quitting.\n')
            break
        else:
            print('Invalid choice. Valid chocices are 0 to 6.\n')


if __name__ == '__main__':
    main()
