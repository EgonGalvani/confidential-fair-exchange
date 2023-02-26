# Intro
This repo contains the code of fair exchange protocol described in ["FairDrop: a Confidential Fair Exchange Protocol for Media Workers"](https://thesis.unipd.it/handle/20.500.12608/42055) 

# Prerequisite 
Client applications require web3.py and PyNaCl, that can be installed via `pip install web3 PyNaCl`.
The prototype uses Infura API to connect Ethereum network, and a API key is already provided inside the `client/data/settings.json` file. 

# Installation
Clone git repository `git clone https://github.com/EgonGalvani/confidential-fair-exchange.git`

## Smart contract 
The smart contract is defined inside the `contracts/conf-fair-exchange.sol` file. We already provide a version of the smart contract deployed in the Ropsten network, at the address indicated inside the `client/data/settings.json` file. In any case the following sections explain how to compile and deploy a new version of the smart contract. 

### Compilation 
After each modification to the code of the smart contract, it has to be compiled again. We used `etherlime` to compile it, but any other tool can be used. The compiled file has to be placed inside the `build` directory, and renamed `ConfidentialFairExchange.json`. For using `etherlime` the following steps are required: 
 - first, install it via `npm install -g etherlime` 
 - then, from the root directory of the project, execute `etherlime compile`, the compiled file will be automatically created in the `build` directory 
 
### Deployment 
To deply the smart contract, the script `client/deployer.py` can be used. It deploys the smart contract inside the Ropsten testnet and it creates the `client/data/settings.json` file. This file contains the rpc url used for the communication with the blockchain, the contract address and other information about the wallets used by the scripts. 

## Offline data generation 
To create some sample data for testing, the `client/offline_data_generator.py` script can be used. It creates two files inside the `data` repository: 
 - `shared.json` that contains the information regarding the files that is shared publicly
 - `master_keys.json` that contains the master keys associated to each file 

# Usage
We provide two main scripts: `client/seller.py` and `client/buyer.py`, that as the names suggest, allow to manage operations for seller and buyer respectively. Both scripts provide a simple user interface that allows to easily interact with the smart contract. Example of usage:  
https://user-images.githubusercontent.com/27569184/190029652-9307432c-08da-4316-8082-6d508c679286.mp4

# Settings 
The file `client/data/settings.json` contains all the settings used by the scripts. 

## Change wallets 
To modify the private key of the wallets associated to seller or buyer, it is necessary to modify the corresponding fields inside the settings file. Also, in case of future deploys, it is necessary to modify the lines 43, 44, 45 in the `deployer.py` script. 

## Change network 
The scripts communicate with the network via a provider variable, that is usually initialized at the beginning of each file. If you want to modify the rpc url used, then it is possilble to do it by modifying the `settings.json` file. Otherwise, if you want to change the provider type, it is necessary to modify: 
 - lines 25/26 of `seller.py`
 - lines 25/26 of `buyer.py`
 - in the case of new deploy, lines 10/11/12 of `deployer.py`
