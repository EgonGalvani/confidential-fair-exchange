pragma solidity >=0.6 <0.7.0;

contract FairDEx {
    address payable seller;
    address payable buyer = BUYER_ADDRESS_HERE;

    // Added 10 minutes to timeout in each function call.
    uint timeout;

    uint constant depth= DEPTH_OF_MERKLE_TREE;
    uint constant price = GOODS_PRICE;

    bytes32 description;
    bytes32 public masterKey;

    enum State { Created, Paid, Published, Inactive }
    // Initial value of state is State.Created.
    State public state;

    event PaidWithDescription();
    event PublishedMasterKey();
    event ExecutionCompleted();

    constructor() public payable {
        seller = msg.sender;
    }

    // Deposit the goods' price and assign description.
    function PayWithDescription(bytes32 _description)
        public
        only(buyer, State.Created, msg.value == price)
        payable
    {
        emit PaidWithDescription();
        state = State.Paid;
        description = _description;
        timeout = now + 10 minutes;
    }

    // Refund to buyer if seller does not publish master key in time.
    function RefundToBuyer()
        public
        only(buyer, State.Paid, now > timeout)
        payable
    {
        emit ExecutionCompleted();
        state = State.Inactive;
        selfdestruct(buyer);
    }

    // Publish the master key.
    function PublishMasterKey(bytes32 _masterKey)
        public
        only(seller, State.Paid, true)
    {
        emit PublishedMasterKey();
        state = State.Published;
        masterKey = _masterKey;
        timeout = now + 10 minutes;
    }

    // Complain about the goods by proving that 
    //  i. a committed subkey is different from the subkey derived from the master key; and
    // ii. and this committed subkey is part of the description.
    function RaiseObjection(uint _committed_ri, bytes32 _committedSubKey, bytes32[] memory _merkleTreePath)
        public
        only(buyer, State.Published, now < timeout)
        payable
    {
        bytes32 computedSubkey = keccak256(abi.encode(masterKey, _committed_ri));
        // Check if the subkey supplied by buyer is different from the subkey derived from masterKey.
        if (computedSubkey != _committedSubKey)
        {
            bytes32 committedNode = keccak256(abi.encode(_committedSubKey, _committed_ri));
            
            // When the loop exits, committedNode will hold the root of Merkle Tree.
            for (uint i = 0; i < depth; i++)
                committedNode = keccak256(abi.encode(committedNode, _merkleTreePath[i]));
            
            // Check if the root equals description.
            if (committedNode == description)
            {
                // If so, the buyer is right and gets the deposit back.
                emit ExecutionCompleted();
                state = State.Inactive;
                selfdestruct(buyer);
            }
        }
    }

    // If objection timeouts, transfer the balance to seller and destruct the contract.
    function TransferToSeller()
        public
        only(seller, State.Published, now > timeout)
    {
        emit ExecutionCompleted();
        state = State.Inactive;
        selfdestruct(seller);
    }

    // Check if all required conditions are satisfied.
    modifier only(address _address, State _state, bool _condition)
    {
        require(msg.sender == _address);
        require(state == _state);
        require(_condition);
        _;
    }
}
