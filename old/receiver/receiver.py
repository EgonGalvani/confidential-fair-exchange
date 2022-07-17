#!/usr/bin/env python3

import json
from web3 import Web3

with open('receiver.conf', 'r') as conf_file:
    conf = [line.strip().split('=')[1] for line in conf_file.readlines()]

infura_url = conf[0]
receiver = conf[1]
receiver_private = conf[2]
contract_address = conf[3]
gas_price = conf[4]
desc_depth = int(conf[5])

web3 = Web3(Web3.WebsocketProvider(infura_url))

with open('fairdex.abi', 'r') as abifile:
    abi = json.load(abifile)

checksum_address = web3.toChecksumAddress(contract_address)
contract = web3.eth.contract(address=checksum_address, abi=abi)

sampled_keys = []
sampled_indices = []
nodes = []
number_of_sampled_keys = 2 ** desc_depth

with open('offchain.txt', 'r') as offline_message:
    lines = [line.strip() for line in offline_message.readlines()]

    for i in range(number_of_sampled_keys):
        sk, r = lines[i].split()
        sampled_keys.append(sk)
        sampled_indices.append(int(r))
        nd = Web3.solidityKeccak(['bytes32', 'uint256'], [sk, int(r)])
        nodes.append(nd)

description = calculate_merkle_root(nodes)
m_proof = calculate_merkle_proof()

def calculate_merkle_root(, arr):
length = len(arr)

if length == 2:
    result = Web3.solidityKeccak(['bytes32', 'bytes32'], [arr[0], arr[1]])
else:
    left_arr = arr[:length // 2]
    right_arr = arr[length // 2:]
    left_hash = calculate_merkle_root(left_arr)
    right_hash = calculate_merkle_root(right_arr)
    result = Web3.solidityKeccak(['bytes32', 'bytes32'], [left_hash, right_hash])

return result

# consider as wrong the first node (node = hash(index, subkey[index]) )
# create the merkle poof considering it as wrong
def calculate_merkle_proof():
    result = [nodes[1]] 
    start_pos = 2

    for i in range(1, desc_depth):
        chunk_size = 2 ** i
        end_pos = start_pos + chunk_size
        arr = nodes[start_pos:end_pos]
        result.append(calculate_merkle_root(arr))
        start_pos = end_pos

    return result

def pay_with_description():
nonce = web3.eth.getTransactionCount(receiver)
transaction = contract.functions.PayWithDescription(description).buildTransaction({
    'gas': 3000000,
    'gasPrice': web3.toWei(gas_price, 'gwei'),
    'from': receiver,
    'nonce': nonce,
    'value': web3.toWei(100, 'finney')  # 0.1 ether
})
signed_txn = web3.eth.account.signTransaction(transaction, private_key=receiver_private)
tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
return tx_hash

def raise_objection():
nonce = web3.eth.getTransactionCount(receiver)
transaction = contract.functions.RaiseObjection(sampled_indices[0], sampled_keys[0],
                                                        m_proof).buildTransaction({
    'gas': 3000000,
    'gasPrice': web3.toWei(gas_price, 'gwei'),
    'from': receiver,
    'nonce': nonce,
})
signed_txn = web3.eth.account.signTransaction(transaction, private_key=receiver_private)
tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
return tx_hash

def refund_to_buyer():
nonce = web3.eth.getTransactionCount(receiver)
transaction = contract.functions.RefundToBuyer().buildTransaction({
    'gas': 3000000,
    'gasPrice': web3.toWei(gas_price, 'gwei'),
    'from': receiver,
    'nonce': nonce
})
signed_txn = web3.eth.account.signTransaction(transaction, private_key=receiver_private)
tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
return tx_hash

def get_master_key():
state = get_contract_state()
if state == 'Published':
    master_key = contract.functions.masterKey().call()
    return Web3.toHex(master_key)
else:
    return 'n/a'

def get_contract_state():
try:
    state = contract.functions.state().call()
    if state == 0:
        return 'Created'
    elif state == 1:
        return 'Paid'
    elif state == 2:
        return 'Published'
except:
    return 'Inactive'

def get_balance():
balance_wei = web3.eth.getBalance(receiver)
balance_eth = web3.fromWei(balance_wei, 'ether')
return balance_eth

