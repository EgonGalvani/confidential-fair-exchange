// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.7.0 <0.9.0;
pragma experimental ABIEncoderV2;

contract ConfidentialFairExchange {
   
    uint constant public MAX_INTERVAL = 3600; // 1 h timemax inteval between operations 
    uint constant public COLLATERAL = 100 wei; // TODO: substitute with actual depth-depending cost 

    /******** INIT PHASE *******/
    event FileRandomness(bytes32 indexed fileHash, uint randomness); 
    event FilePublished(bytes32 indexed fileHash, bytes32 description); 

    // struct containing info about the file to sell 
    struct FileInfo {
        address seller; 
        uint depth;  // description depth   
        uint price; 
        bytes32 description; 
    }

    // mapping associating to each hash the corrisponding FileInfo struct 
    mapping(bytes32 => FileInfo) public fileInfos; 

    function publishFile(bytes32 _fileHash, uint _depth, uint _price) public {
        require(fileInfos[_fileHash].seller == address(0), "The file has already been published"); 

        fileInfos[_fileHash] = FileInfo(msg.sender, _depth, _price, 0); 
        emit FileRandomness(_fileHash, uint(keccak256(abi.encodePacked(block.difficulty, block.timestamp))));
    }

    function publishDescription(bytes32 _fileHash, bytes32 _description) public {
        require(fileInfos[_fileHash].seller == msg.sender, "Only the seller can set the description"); 
        require(fileInfos[_fileHash].description == 0, "The description has already been set"); 

        fileInfos[_fileHash].description = _description; 
        emit FilePublished(_fileHash, _description);
    }

    /**** BUYING PHASE *****/
    event PurchaseRequested(bytes32 indexed fileHash, bytes32 indexed purchaseID, bytes32 secretHash, bytes encryptedSecret); 
    event EncryptedKeyPublished(bytes32 indexed purchaseID, bytes32 encryptedKey); 

    enum State { Requested, EncryptedKeyShared, Completed, Invalid, Timeout} 
    struct Purchase { 
        address buyer; 
        uint lastOperationTime; 
        State state; 
        bytes32 encryptedKey;
        bytes32 secretHash;  
    }

    mapping(bytes32 => Purchase) purchases; 
    function buy(bytes32 _fileHash, bytes32 _secretHash, bytes calldata _encryptedSecret) 
        public payable {
        
        require(fileInfos[_fileHash].seller != address(0), "No file with requested hash is present inside the system"); 
        require(fileInfos[_fileHash].description != 0, "The considered file has not description set yet");  
        require(msg.value == fileInfos[_fileHash].price, "The sent amount of money is lower than the file price"); 

        bytes32 purchaseID = bytes32(keccak256(abi.encodePacked(msg.sender, _fileHash)));        
        require(purchases[purchaseID].state == State.Requested, "Purchase already started"); 
        purchases[purchaseID] = Purchase(msg.sender, block.timestamp, State.Requested, 0, _secretHash);  

        emit PurchaseRequested(_fileHash, purchaseID, _secretHash, _encryptedSecret);
    }

    /* buyer call buy -> seller check H(D(_encryptedSecret)) == _secretHash  
        -> if false: wait MAX_INTERVAL and call withdraw 
        -> if true: call publishKey (with collateral)
    */ 
    function publishKey(bytes32 _encryptedKey, bytes32 _fileHash, bytes32 _purchaseID) 
        Only(_fileHash, _purchaseID, State.Requested, fileInfos[_fileHash].seller)
        InTime(_purchaseID) 
        public payable {
        
        purchases[_purchaseID].encryptedKey = _encryptedKey; 
        purchases[_purchaseID].state = State.EncryptedKeyShared; 
        purchases[_purchaseID].lastOperationTime = block.timestamp; 
        emit EncryptedKeyPublished(_purchaseID, _encryptedKey);
    }

    // Complain about the goods by proving that 
    //  i. a committed subkey is different from the subkey derived from the master key; and
    // ii. and this committed subkey is part of the description.
    struct POM {
        uint _committed_ri; 
        bytes32 _committedSubKey; 
        bytes32[] _merkleTreePath; 
    }
    function raiseObjection(bytes32 _fileHash, bytes32 _purchaseID, bytes32 _secret,
        POM memory pom)
        Only(_fileHash, _purchaseID, State.EncryptedKeyShared, purchases[_purchaseID].buyer)
        InTime(_purchaseID)
        public
        payable
    {
        require(keccak256(abi.encodePacked(_secret)) == purchases[_purchaseID].secretHash, "Provided secret is wrong"); 
        bytes32 key = purchases[_purchaseID].encryptedKey ^ _secret; 
        
        bytes32 computedSubkey = keccak256(abi.encodePacked(key, pom._committed_ri));
        // Check if the subkey supplied by buyer is different from the subkey derived from masterKey.
        if (computedSubkey != pom._committedSubKey) {
            bytes32 committedNode = keccak256(abi.encodePacked(pom._committedSubKey, pom._committed_ri));
            
            // When the loop exits, committedNode will hold the root of Merkle Tree.
            for (uint i = 0; i < fileInfos[_fileHash].depth; i++)
                committedNode = keccak256(abi.encodePacked(committedNode, pom._merkleTreePath[i]));
            
            // Check if the root equals description.
            if (committedNode == fileInfos[_fileHash].description) {
                // If so, the buyer is right and gets the deposit + collateral back.
                purchases[_purchaseID].state = State.Invalid; 
                payable(msg.sender).transfer(COLLATERAL + fileInfos[_fileHash].price);
            }
        }
    }

    // Refund to buyer if seller does not publish master key in time.   
    function refundToBuyer(bytes32 _fileHash, bytes32 _purchaseID)
        Only(_fileHash, _purchaseID, State.Requested, purchases[_purchaseID].buyer)
        public payable {
        
        require(purchases[_purchaseID].lastOperationTime + MAX_INTERVAL < block.timestamp, "The seller has still time to share the encrypted key"); 
        purchases[_purchaseID].state = State.Timeout; 
        payable(msg.sender).transfer(fileInfos[_fileHash].price);
    }

    function withdraw(bytes32 _fileHash, bytes32 _purchaseID) 
        Only(_fileHash, _purchaseID, State.EncryptedKeyShared, fileInfos[_fileHash].seller)
        public payable 
    {
        require(purchases[_purchaseID].lastOperationTime + MAX_INTERVAL < block.timestamp, "The buyer has still time to share a POM"); 
        purchases[_purchaseID].state = State.Completed; 
        payable(msg.sender).transfer(fileInfos[_fileHash].price + COLLATERAL);
    }
     
    modifier InTime(bytes32 _purchaseID) {
        require(block.timestamp <= purchases[_purchaseID].lastOperationTime + MAX_INTERVAL, "Max timeout reached"); 
        _; 
    }

    modifier Only(bytes32 _fileHash, bytes32 _purchaseID, State _state, address caller) {
        require(bytes32(keccak256(abi.encodePacked(purchases[_purchaseID].buyer, _fileHash))) == _purchaseID, "Wrong purchase ID"); 
        require(purchases[_purchaseID].state == _state, "Purchase in the wrong state"); 
        require(msg.sender == caller, "Wrong function caller"); 
        _;
    }
}