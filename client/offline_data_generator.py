from web3 import Web3
import json
import secrets 
from offline_crypto import get_public_key

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

f = open("./data/settings.json", "r")
settings = json.loads(f.read())
f.close() 

file_infos = []
master_keys_info = []

subkey_depth = 14
number_of_subkeys = 2 ** subkey_depth

for desc_depth in range(6, 15): # 6 to 14 
  master_key = "0x" + secrets.token_hex(32)

  # simulate the file hash 
  file_hash = "0x" + secrets.token_hex(32)

  # simulation of random indices agreement  
  number_of_random_indices = 2 ** desc_depth
  secure_random = secrets.SystemRandom()
  random_indices = secure_random.sample(range(number_of_subkeys), number_of_random_indices)

  # generate only the subkeys that we need 
  subkeys = {}
  for random_index in random_indices:
    sk = Web3.solidityKeccak(['bytes32', 'uint256'], [master_key, random_index])
    subkeys[random_index] = sk.hex() 

  # compute descriton
  nodes = []
  for random_index in random_indices: 
    node = Web3.solidityKeccak(['bytes32', 'uint256'], [subkeys[random_index], random_index])
    nodes.append(node)
  description = calculate_merkle_root(nodes) 

  # add object to array
  file_infos.append({
    "file_hash": file_hash, 
    "desc": description.hex(), 
    "desc_depth": desc_depth, 
    "file_price": 100, 
    "public_key": "0x" + get_public_key(settings["seller"]["private_key"]).hex() , 
    "samp": list(map(lambda random_index: {"index": random_index, "value": subkeys[random_index]}, random_indices))
  }); 
  
  master_keys_info.append({
    "file_hash": file_hash, 
    "master_key": str(master_key)
  })

#for r in random_indices:
#  offline_message.write(f'{Web3.toHex(subkeys[r])} {r}\n')

with open('./data/shared.json', 'w') as f:
  json.dump(file_infos, f, indent=2, separators=(',', ': '))

with open('./data/master_keys.json', 'w') as f:
  json.dump(master_keys_info, f, indent=2, separators=(',', ': '))