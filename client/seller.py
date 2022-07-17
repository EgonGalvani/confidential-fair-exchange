#!/usr/bin/env python3

import json
import secrets
from web3 import Web3 
from web3.middleware import geth_poa_middleware
from utils import get_events, subscribe_to_event, sign_and_wait

def load_data(): 
  f = open("./data/settings.json", "r")
  settings = json.loads(f.read())
  f.close() 

  f = open("./data/shared.json", "r")
  shared = json.loads(f.read())
  f.close() 

  f = open("./data/master_keys.json", "r")
  master_keys = json.loads(f.read())
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

# function publishFile(bytes32 _fileHash, uint _depth, uint _price, bytes32 _sellerPublicKey) public {
def publish_file(file_hash, desc_depth, seller_public_key) :
  nonce = web3.eth.getTransactionCount(settings["seller"]["address"])
  transaction = contract.functions.publishFile(file_hash, desc_depth, settings["file_price"], seller_public_key).buildTransaction(
    {
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["seller"]["address"],
      'nonce': nonce,
      #'value': settings["file_price"]
    }
  )

  print("Publishing file sale opportunity...")
  return sign_and_wait(web3, transaction, settings["seller"]["private_key"])

# function publishDescription(bytes32 _fileHash, bytes32 _description) public {
def publish_description(file_hash, description) :
  nonce = web3.eth.getTransactionCount(settings["seller"]["address"])
  transaction = contract.functions.publishDescription(file_hash, description).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["seller"]["address"],
      'nonce': nonce,
  })

  print("Publishing description...")
  return sign_and_wait(web3, transaction, settings["seller"]["private_key"])

# function publishKey(bytes32 _encryptedKey, bytes32 _fileHash, bytes32 _purchaseID) 
def publish_master_key(encrypted_master_key, file_hash, purchase_ID):
  nonce = web3.eth.getTransactionCount(settings["seller"]["address"])
  collateral = contract.functions.COLLATERAL().call(); 

  transaction = contract.functions.publishKey(encrypted_master_key, file_hash, purchase_ID).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["seller"]["address"],
      'nonce': nonce,
      'value': collateral
  })

  print("Publishing encrypted master key...")
  return sign_and_wait(web3, transaction, settings["seller"]["private_key"])

# function withdraw(bytes32 _fileHash, bytes32 _purchaseID) 
def withdraw(file_hash, purchase_ID):
  nonce = web3.eth.getTransactionCount(settings["seller"]["address"])

  transaction = contract.functions.withdraw(file_hash, purchase_ID).buildTransaction({
      # 'gas': 3000000,
      # 'gasPrice': web3.toWei(gas_price, 'gwei'),
      'from': settings["seller"]["address"],
      'nonce': nonce
  })

  print("Requesting withdraw...")
  return sign_and_wait(web3, transaction, settings["seller"]["private_key"])

# first: init all files 
for f in shared: # len(shared) 
  public_key = "0x" + secrets.token_hex(32) # TODO: manage encryption system 
  publish_file(f["file_hash"], f["desc_depth"], public_key) 
  publish_description(f["file_hash"], f["desc"])
  break 

# wait for requests of purchase and share corresponding key 
def callback(event): 
  file_hash = event.args["fileHash"]
  purchase_ID = event.args["purchaseID"]

  print("Received purchase_id: " + str(purchase_ID))

  # TODO: write also the optimistic case 
  # TODO: check on the encryption and hash of the secret 
  
  # pessimistic case: encrypted_master_key = wrong bytes 
  encrypted_master_key = "0x" + secrets.token_hex(32)
  publish_master_key(encrypted_master_key, file_hash, purchase_ID)

print("Listening for purchase requests...")
current_block_number = web3.eth.get_block('latest').number
subscribe_to_event(web3, contract.events.PurchaseRequested, contract.address, callback, current_block_number)

# publish_master_key()
