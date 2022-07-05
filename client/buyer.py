#!/usr/bin/env python3

import json
import secrets
from web3 import Web3 
from web3.middleware import geth_poa_middleware

def load_data(): 
  f = open("./data/settings.json", "r")
  settings = json.loads(f.read())
  f.close() 

  f = open("./data/shared.json", "r")
  shared = json.loads(f.read())
  f.close() 

  f = open("./data/master_keys.txt", "r")
  master_keys = f.readlines()
  f.close() 
  return settings, shared, master_keys
settings, shared, master_keys = load_data()

# set up provider
web3 = Web3(Web3.HTTPProvider(settings["rpc_url"]))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

def load_contract(): 
  contract_interface_f = open("./../build/ConfidentialFairExchange.json", "r")
  contract_interface = json.loads(contract_interface_f.read())
  contract_interface_f.close() 

  contract_address = web3.toChecksumAddress(settings["contract_address"])
  contract = web3.eth.contract(address=contract_address, abi=contract_interface["abi"])
  return contract
contract = load_contract()

# function buy(bytes32 _file_hash, bytes32 _secret_hash, bytes32 _encrypted_secret) 
def buy(file_hash, secret_hash, encrypted_secret):
  nonce = web3.eth.getTransactionCount(settings["buyer"]["address"])
  price = settings["file_price"] # in case: call the smart contract 
 
  transaction = contract.functions.publishKey(file_hash, secret_hash, encrypted_secret).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["buyer"]["address"],
      'nonce': nonce,
      'value': price 
  })

  print("Requesting file purchase...")
  return sign_and_wait(transaction)

# function raiseObjection(bytes32 _file_hash, bytes32 _purchase_ID, bytes32 _secret, POM memory pom)
def raiseObjection(file_hash, purchase_ID, secret, committed_ri, committedSubKey, merkleTreePath):
  nonce = web3.eth.getTransactionCount(settings["buyer"]["address"])
  pom = (committed_ri, committedSubKey, merkleTreePath) # struct represent as tuple 

  transaction = contract.functions.publishKey(file_hash, purchase_ID, secret, pom).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["buyer"]["address"],
      'nonce': nonce,
  })

  print("Requesting objection raising...")
  return sign_and_wait(transaction)

# function refoundToBuyer(bytes32 _file_hash, bytes32 _purchase_ID)
def refundToBuyer(file_hash, purchase_ID):
  nonce = web3.eth.getTransactionCount(settings["buyer"]["address"])

  transaction = contract.functions.refoundToBuyer(file_hash, purchase_ID).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["buyer"]["address"],
      'nonce': nonce,
  })

  print("Requesting refund to buyer...")
  return sign_and_wait(transaction)

def sign_and_wait(transaction):
  signed_txn = web3.eth.account.signTransaction(transaction, private_key=settings["buyer"]["private_key"])
  tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
  tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
  
  print("Transaction correctly executed")
  return tx_receipt

def calculate_merkle_root(arr):
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
def calculate_merkle_proof(nodes, desc_depth):
  result = [nodes[1]] 
  start_pos = 2

  for i in range(1, desc_depth):
    chunk_size = 2 ** i
    end_pos = start_pos + chunk_size
    arr = nodes[start_pos:end_pos]
    result.append(calculate_merkle_root(arr))
    start_pos = end_pos

  return result

# TODO: get list of events of published sales 
available_files = [] # each event will have a fileHash  

for available_file, index in enumerate(available_files): 
  
  # secret creation 
  secret = "0x" + secrets.token_hex(32) # TODO: check types 
  secret_hash = Web3.solidityKeccak(['bytes32'], [secret])
  secret_encrypted = "" 
  
  # buy request 
  buy(available_file.fileHash, secret_hash, secret_encrypted) 
  
  # TODO: wait for the event with the purchaseID
  purchase_event = {purchaseID: ""}

  # TODO: wait for the key 
  key_reveal_event = {}

  # consider the pessimistic case: 
  nodes = []
  for desc_el_index, desc_el_value in shared[index]["samp"]: # for each element (index, value) that compose the description 
    node = Web3.solidityKeccak(['bytes32', 'uint256'], [desc_el_value, desc_el_index])
    nodes.append(node)
  proof = calculate_merkle_proof(nodes, shared[index]["desc_depth"] ) 

  # raiseObjection 
  raiseObjection(available_file.fileHash, purchase_event.purchaseID, secret,
    shared[index]["samp"][0]["index"], shared[index]["samp"][0]["value"], proof)

  # refundToBuyer 
  refundToBuyer(available_file.fileHash, purchase_event.purchaseID)