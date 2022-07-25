from web3 import Web3 
from web3.middleware import geth_poa_middleware
from eth_account import Account
import secrets
import json

# https://ropsten.infura.io/v3/0e65b81adc554fa889b8ac769a89d543

# set up provider
provider_rpc_url =  "https://ropsten.infura.io/v3/0e65b81adc554fa889b8ac769a89d543" #"https://rpc-mumbai.maticvigil.com/"
web3 = Web3(Web3.HTTPProvider(provider_rpc_url))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

def generate_wallet(): 
  priv = secrets.token_hex(32)
  private_key = "0x" + priv
  acct = Account.from_key(private_key)
  return private_key, acct.address

def deploy_contact(contract_interface, deployer_wallet): 

  construct_txn = web3.eth.contract(
        abi=contract_interface['abi'],
        bytecode=contract_interface['bytecode']).constructor().buildTransaction(
    {
        'from': deployer_wallet['address'],
        'nonce': web3.eth.get_transaction_count(deployer_wallet['address']),
    }
  ) 
  
  # Sign tx with PK
  tx_create = web3.eth.account.sign_transaction(construct_txn, deployer_wallet['private_key'])

  # Send tx and wait for receipt
  tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)
  tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
  
  print(f'Contract deployed at address: { tx_receipt.contractAddress }')
  return tx_receipt 
  
seller_private_key, seller_address = "0xc718adce055a99f9f81ec53b8d058ae372ba838b471eb5b5db49d79dc27a017f", "0xA616272ABC03a4F2c9c51A1E33d76b4b1f4d2BFd"# generate_wallet()
buyer_private_key, buyer_address =  "0x25054a40b295fbe002f9df9427dd5b6b0801edd25b30c4a1236b7a087421ed7b", "0x9E18Bc0Cb016bF9BE05eBc9dDe59f8bc63AeF081"
deployer_private_key, deployer_address = "0xe65bfddbccd18cfe199973521cc284d77567412ea76e9ee3007a11418eb772fd", "0xAaeF0BFc1258800018b92FB63b4DeAd6ADf38b4B"

print("Deployer address and private key " + deployer_address + " " + deployer_private_key)
input("Please insert balance inside deployer wallet, click when done...") 

# load contract interface
contract_interface_f = open("./../build/ConfidentialFairExchange.json", "r")
contract_interface = json.loads(contract_interface_f.read())
contract_interface_f.close() 

deploy_tx_receipt = deploy_contact(
  contract_interface, 
  {
    'private_key': deployer_private_key, 
    'address': deployer_address
  }) 

print(deploy_tx_receipt)

settings_obj = {
  "rpc_url": provider_rpc_url, 
  "contract_address": deploy_tx_receipt.contractAddress, 
  "seller": {
    "private_key": seller_private_key, 
    "address": seller_address
  }, 
  "buyer": {
    "private_key": buyer_private_key, 
    "address": buyer_address
  }, 
  "deployer": {
    "private_key": deployer_private_key,
    "address": deployer_address
  }
}

with open('./data/settings.json', 'w') as f:
  json.dump(settings_obj, f, indent=2, separators=(',', ': '))
