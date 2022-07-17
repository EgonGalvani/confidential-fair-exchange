from web3._utils.events import get_event_data
import asyncio
from web3 import Web3

def sign_and_wait(web3, transaction, private_key):
  signed_txn = web3.eth.account.signTransaction(transaction, private_key=private_key)
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

def get_events(web3, event_template, contract_address, from_block="", to_block="latest", filter = None): 
  if from_block == "": 
    from_block = web3.eth.get_block('latest').number -950

  events = []
  # print("Requesting logs from " + str(from_block) + " to " + str(to_block) + " at address: " + str(contract_address))
  raw_events = web3.eth.get_logs({'fromBlock': from_block, 'toBlock': to_block, 'address': contract_address})
  for event in raw_events: 
    try: 
      event_data = get_event_data(event_template.web3.codec, event_template._get_event_abi(), event) 
      events.append(event_data)
    except: 
      pass

  if filter is None: 
    return events 

  filtered_events = []
  for event in events: 
    for key, value in filter.items():    
      if event.args[key] != value: 
        continue
      filtered_events.append(event)

  return filtered_events

async def _wait_event(web3, event_template, contract_address, from_block, poll_interval, filters, once = False, callback = None):  
  while True: 
    latest_block = web3.eth.get_block('latest').number
    if latest_block < from_block: 
      await asyncio.sleep(poll_interval)
      continue 

    try: 
      new_events = get_events(web3, event_template, contract_address, from_block, latest_block, filters)
    except: 
      print("Error in eth.get_events")
      await asyncio.sleep(poll_interval)
      continue 

    if len(new_events) > 0: 
      if once: 
        if callback is not None: 
          callback(new_events[0])
        else: 
          return new_events[0] 
      else: 
        if callback is not None: 
          for event in new_events:
            callback(event)
    
    from_block = latest_block+1
    await asyncio.sleep(poll_interval)

def wait_event_once(web3, event_template, contract_address, from_block, filters=None): 
  loop = asyncio.get_event_loop() 
  event = loop.run_until_complete(asyncio.gather(_wait_event(web3, event_template, contract_address, from_block, 5, filters, True)))
  loop.close() 
  return event  

def subscribe_to_event(web3, event_template, contract_address, callback, from_block, filters=None): 
  loop = asyncio.get_event_loop() 
  loop.run_until_complete(asyncio.gather(_wait_event(web3, event_template, contract_address, from_block, 5, filters, False, callback)))
  loop.close() 