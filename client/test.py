from web3 import Web3
import json 

f = open("./data/settings.json", "r")
settings = json.loads(f.read())
f.close() 

ganache_url = settings["rpc_url"]
web3 = Web3(Web3.HTTPProvider(ganache_url))
account_1 = settings["deployer"]["address"]
private_key1 = settings["deployer"]["private_key"]
account_2 = settings["seller"]["address"]

#get the nonce.  Prevents one from sending the transaction twice
nonce = web3.eth.getTransactionCount(account_1)

#build a transaction in a dictionary
tx = {
  'nonce': nonce,
  'to': account_2,
  'value': web3.toWei(0.3, 'ether'),
  'gas': 3000000,
  'gasPrice': web3.toWei(40, 'gwei'),
}

#sign the transaction
signed_tx = web3.eth.account.sign_transaction(tx, private_key1)

#send transaction
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)

#get transaction hash
print(web3.toHex(tx_hash))