from web3 import Web3
import json 

f = open("./data/settings.json", "r")
settings = json.loads(f.read())
f.close() 

ganache_url = settings["rpc_url"]
web3 = Web3(Web3.HTTPProvider(ganache_url))
from_wallet = settings["deployer"]

to = settings["buyer"]["address"]

#get the nonce.  Prevents one from sending the transaction twice
nonce = web3.eth.getTransactionCount(from_wallet["address"])

#build a transaction in a dictionary
tx = {
  'nonce': nonce,
  'to': to,
  'value': web3.toWei(0.3, 'ether'),
  'gas': 3000000,
  'gasPrice': web3.toWei(40, 'gwei'),
}

#sign the transaction
signed_tx = web3.eth.account.sign_transaction(tx, from_wallet["private_key"])

#send transaction
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)

#get transaction hash
print(web3.toHex(tx_hash))