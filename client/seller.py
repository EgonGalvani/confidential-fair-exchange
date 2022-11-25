#!/usr/bin/env python3

import json
import secrets
from web3 import Web3 
from web3.middleware import geth_poa_middleware
from utils import get_events, subscribe_to_event, sign_and_wait, byte_xor
from offline_crypto import _hex_to_bytes, decrypt_nacl

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
def publish_file(file_hash, price, desc_depth) :
  nonce = web3.eth.getTransactionCount(settings["seller"]["address"])
  transaction = contract.functions.publishFile(file_hash, desc_depth, price).buildTransaction(
    {
      'gas': 3000000,
      'gasPrice': web3.toWei(settings["eth_gas_price"], 'gwei'),
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
      'gas': 3000000,
      'gasPrice': web3.toWei(settings["eth_gas_price"], 'gwei'),
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
      'gas': 3000000,
      'gasPrice': web3.toWei(settings["eth_gas_price"], 'gwei'),
      'from': settings["seller"]["address"],
      'nonce': nonce,
      'value': collateral
  })

  return sign_and_wait(web3, transaction, settings["seller"]["private_key"])

# function withdraw(bytes32 _fileHash, bytes32 _purchaseID) 
def withdraw(file_hash, purchase_ID):
  nonce = web3.eth.getTransactionCount(settings["seller"]["address"])

  transaction = contract.functions.withdraw(file_hash, purchase_ID).buildTransaction({
      'gas': 3000000,
      'gasPrice': web3.toWei(settings["eth_gas_price"], 'gwei'),
      'from': settings["seller"]["address"],
      'nonce': nonce
  })

  print("Requesting withdraw...")
  return sign_and_wait(web3, transaction, settings["seller"]["private_key"])

# wait for requests of purchase and share corresponding key 
def callback(event): 
  global optimistic
  file_hash, purchase_ID, secret_hash, encrypted_secret = event.args["fileHash"], event.args["purchaseID"],  event.args["secretHash"],  event.args["encryptedSecret"]

  print("== Received buy request ==")
  print("Purchase ID: 0x" + purchase_ID.hex())
  print("File hash: 0x" + file_hash.hex())

  optimistic = input("Do you want to share the correct key? (Y/N)")
  if optimistic == "Y": 
    optimistic = True
  else: 
    optimistic = False

  # if seller behave in the correct case (share the correct master key)
  if optimistic: 
    hex_file_hash = "0x" + file_hash.hex() 
    file_master_key = None
   
    # find the master key for the requested file 
    for master_key in master_keys: 
      if master_key["file_hash"] == hex_file_hash: 
        file_master_key = master_key["master_key"]
    if file_master_key == None: 
      print("Error corresponding master key not found")
    print("Master key: " + file_master_key)
    
    # decrypt the secret 
    secret = decrypt_nacl(_hex_to_bytes(settings["seller"]["private_key"]), encrypted_secret) 
    print("Secret: 0x" + secret.hex())

    # check that secret corresponds to the published hash  
    secret_hash_computed = Web3.solidityKeccak(['bytes32'], [secret])
    if secret_hash_computed != secret_hash:
      print("Error comparing the two hashes: ")
      print("Secret hash received: " + str(secret_hash))
      print("Secret hash computed: " + str(secret_hash_computed)) 

    encrypted_master_key = byte_xor(_hex_to_bytes(file_master_key), secret)
  else: 
    # pessimistic case: share a wrong master key wrong bytes 
    encrypted_master_key = secrets.token_bytes(32)
  
  print("Publishing key: 0x" + encrypted_master_key.hex())
  publish_master_key(encrypted_master_key, file_hash, purchase_ID)
  print("\n\n")

def print_menu(): 
  print('\nCommands:')
  print(' [1] Init file\t\t[2] Wait for buy requests')
  print(' [3] List files\t\t[4] Check balance')
  print(' [5] Withdraw\t\t[6] Exit\n') 

print('FairDrop')
print('Client Application for Seller')
print()
print(f'Contract: {contract.address}') 
print_menu() 

while True:
  choice = int(input('Enter your choice: '))
  if choice == 1:
    print("Started init procedure")

    for index, f in enumerate(shared): # len(shared) 
      print("  " + str(index) + ") " + str(f["file_hash"]))
  
    # TODO: add possibility to select local file 
    index = int(input("Select index of file to init: "))
    f = shared[index] 
    publish_file(f["file_hash"], f["file_price"],f["desc_depth"]) 
    publish_description(f["file_hash"], f["desc"])
  elif choice == 2:
    print("Listening for purchase requests...")
    current_block_number = web3.eth.get_block('latest').number
    subscribe_to_event(web3, contract.events.PurchaseRequested, contract.address, callback, current_block_number)
  elif choice == 3: 
    print("File hashes: ")
    past_init_events = get_events(web3, contract.events.FilePublished, contract.address)
    for past_init_event in past_init_events: 
      print(" - 0x" + past_init_event.args["fileHash"].hex())
  elif choice == 4: 
    balance = web3.eth.get_balance(settings["seller"]["address"])
    print("Current balance: " + str(web3.fromWei(balance, 'ether')) + " ETH")
  elif choice == 5: 
    file_hash = input("Insert hash of the file to withdraw: ")
    sale_id = input("Insert sale id to withdraw: ")
    withdraw(file_hash, sale_id)
    print("Withdraw executed")
  elif choice == 6: 
    break 
  else:
    print('Invalid choice. Valid chocices are 1 to 5.\n')

  print_menu() 
# first: init all files (FOR PERFORMANCE EVALUATION)
''' 
for index, f in enumerate(shared): # len(shared) 
  print(" == INIT PHASE file with hash: " + f["file_hash"] + " == ")
  publish_file(f["file_hash"], f["file_price"],f["desc_depth"]) 
  publish_description(f["file_hash"], f["desc"])
print("\nFinished INIT phase for all files")
'''