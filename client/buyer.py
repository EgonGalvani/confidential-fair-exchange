#!/usr/bin/env python3

import json
import secrets
from web3 import Web3 
from web3.middleware import geth_poa_middleware
from utils import get_events, sign_and_wait, wait_event_once, calculate_merkle_proof
from offline_crypto import encrypt_nacl, _hex_to_bytes
import warnings
warnings.filterwarnings('ignore')

def load_data(): 
  f = open("./data/settings.json", "r")
  settings = json.loads(f.read())
  f.close() 

  f = open("./data/shared.json", "r")
  shared = json.loads(f.read())
  f.close() 
  return settings, shared
settings, shared = load_data()

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
def buy(file_hash, secret_hash, encrypted_secret, price):
  nonce = web3.eth.getTransactionCount(settings["buyer"]["address"])

  transaction = contract.functions.buy(file_hash, secret_hash, encrypted_secret).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["buyer"]["address"],
      'nonce': nonce,
      'value': price 
  })

  print("Requesting file purchase...")
  return sign_and_wait(web3, transaction, settings["buyer"]["private_key"])

# function raiseObjection(bytes32 _file_hash, bytes32 _purchase_ID, bytes32 _secret, POM memory pom)
def raiseObjection(file_hash, purchase_ID, secret, committed_ri, committedSubKey, merkleTreePath):
  nonce = web3.eth.getTransactionCount(settings["buyer"]["address"])
  pom = (committed_ri, committedSubKey, merkleTreePath) # struct represent as tuple 

  transaction = contract.functions.raiseObjection(file_hash, purchase_ID, secret, pom).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["buyer"]["address"],
      'nonce': nonce,
  })

  print("Requesting objection raising...")
  return sign_and_wait(web3, transaction, settings["buyer"]["private_key"])

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
  return sign_and_wait(web3, transaction, settings["buyer"]["private_key"])

# get list of events of published sales 
# available_files = get_events(web3, contract.events.FilePublished, contract.address, from_block=27202643, to_block=27203643)
# print(available_files)

'''
execute: 
 - first the optimistic case on the first file 
 - then the pessimistic case on all the files  
'''

optimistic = True 

files = list(enumerate(shared)) 
files.insert(0, files[0])

# assume at this point the seller has already initialize the files inside the smart contract 
for index, file_to_buy in files: 
  
  msg = "Managing file with index: " + str(index) + " and hash: " + str(file_to_buy["file_hash"]) 
  if optimistic: 
    msg = "[OPTIMISTIC] " + msg 
  else: 
    msg = "[PESSIMISTIC] " + msg 
  print(msg)

  # secret creation 
  secret = secrets.token_bytes(32) 
  secret_hash = Web3.solidityKeccak(['bytes32'], [secret])
  secret_encrypted = encrypt_nacl(_hex_to_bytes(file_to_buy["public_key"]), secret)
  
  # buy request 
  buy_receipt = buy(file_to_buy["file_hash"], secret_hash, secret_encrypted, file_to_buy["file_price"]) 
  purchase_event = contract.events.PurchaseRequested().processReceipt(buy_receipt)
  purchase_ID = purchase_event[0].args["purchaseID"] 
  print("current purchase_id: ") 
  print(purchase_ID)

  # wait for the key 
  print("Waiting for the buyer to publish the key... ")
  key_reveal_event = wait_event_once(web3, contract.events.EncryptedKeyPublished, contract.address, purchase_event[0].blockNumber, {"purchaseID": purchase_ID})
  key = key_reveal_event[0].args["encryptedKey"]
  print("Received key: ")
  print(key)
  
  if optimistic: 
    optimistic = False
  else: 
    # consider the pessimistic case: 
    nodes = []
    for desc_element in shared[index]["samp"]: # for each element (index, value) that compose the description 
      desc_el_index, desc_el_value = desc_element["index"], desc_element["value"]
      node = Web3.solidityKeccak(['bytes32', 'uint256'], [desc_el_value, desc_el_index])
      nodes.append(node)
    proof = calculate_merkle_proof(nodes, shared[index]["desc_depth"] ) 
    
    #  balance = web3.eth.get_balance(settings["buyer"]["address"])
    #  print("Balance before objection: " + str(balance))

    # raiseObjection: consider the case where the first key is the wrong one  
    raiseObjection(file_to_buy["file_hash"], purchase_ID, secret,
      shared[index]["samp"][0]["index"], shared[index]["samp"][0]["value"], proof)
    
    #  balance = web3.eth.get_balance(settings["buyer"]["address"])
    #  print("Balance after objection: " + str(balance))

  print("\n")