// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Escrow
 * @dev Multi-Agent Escrow Smart Contract with Two-Stage Dispute Arbitration & Timeout Exit Paths
 */
contract Escrow {
    enum State { Created, Funded, DeliverySignaled, Confirmed, Disputed, Released, Refunded }

    enum Ruling { ReleaseToSeller, RefundToBuyer, Split }

    address payable public immutable buyer;
    address payable public immutable seller;
    address public immutable arbitrator;

    bytes32 public immutable transcriptHash;
    bytes32 public evidenceHash;
    bytes32 public disputeEvidenceHash;

    uint256 public amountLocked;
    uint256 public fundedAt;
    uint256 public deliverySignaledAt;

    uint256 public immutable deliveryConfirmTimeout;
    uint256 public immutable disputeWindow;

    State public currentState;

    event Funded(address indexed buyer, uint256 amount, uint256 timestamp);
    event DeliverySignaled(address indexed seller, bytes32 evidenceHash, uint256 timestamp);
    event Confirmed(address indexed buyer, uint256 timestamp);
    event Disputed(address indexed buyer, bytes32 disputeEvidenceHash, uint256 timestamp);
    event Arbitrated(uint8 decision, uint8 sellerPct, uint256 sellerAmount, uint256 buyerAmount);
    event FundsReleased(address indexed recipient, uint256 amount);
    event FundsRefunded(address indexed recipient, uint256 amount);

    modifier onlyBuyer() {
        require(msg.sender == buyer, "Escrow: only buyer allowed");
        _;
    }

    modifier onlySeller() {
        require(msg.sender == seller, "Escrow: only seller allowed");
        _;
    }

    modifier onlyArbitrator() {
        require(msg.sender == arbitrator, "Escrow: only arbitrator allowed");
        _;
    }

    modifier inState(State expectedState) {
        require(currentState == expectedState, "Escrow: invalid state transition");
        _;
    }

    constructor(
        address payable _seller,
        address _arbitrator,
        bytes32 _transcriptHash,
        uint256 _deliveryConfirmTimeout,
        uint256 _disputeWindow
    ) {
        require(_seller != address(0), "Escrow: invalid seller address");
        require(_arbitrator != address(0), "Escrow: invalid arbitrator address");
        require(_seller != msg.sender, "Escrow: buyer and seller must differ");

        buyer = payable(msg.sender);
        seller = _seller;
        arbitrator = _arbitrator;
        transcriptHash = _transcriptHash;

        deliveryConfirmTimeout = _deliveryConfirmTimeout > 0 ? _deliveryConfirmTimeout : 3600;
        disputeWindow = _disputeWindow > 0 ? _disputeWindow : 3600;

        currentState = State.Created;
    }

    /**
     * @dev Buyer locks funds in escrow.
     */
    function fund() external payable onlyBuyer inState(State.Created) {
        require(msg.value > 0, "Escrow: funding amount must be > 0");

        amountLocked = msg.value;
        fundedAt = block.timestamp;
        currentState = State.Funded;

        emit Funded(buyer, msg.value, block.timestamp);
    }

    /**
     * @dev Seller signals delivery with a commitment evidence hash.
     */
    function signalDelivery(bytes32 _evidenceHash) external onlySeller inState(State.Funded) {
        require(_evidenceHash != bytes32(0), "Escrow: empty evidence hash");

        evidenceHash = _evidenceHash;
        deliverySignaledAt = block.timestamp;
        currentState = State.DeliverySignaled;

        emit DeliverySignaled(seller, _evidenceHash, block.timestamp);
    }

    /**
     * @dev Buyer confirms delivery, releasing funds to seller.
     */
    function confirmDelivery() external onlyBuyer {
        require(
            currentState == State.Funded || currentState == State.DeliverySignaled,
            "Escrow: cannot confirm in current state"
        );

        currentState = State.Confirmed;
        emit Confirmed(buyer, block.timestamp);

        _releaseFunds();
    }

    /**
     * @dev Buyer disputes delivery within the allowed dispute window.
     */
    function disputeDelivery(bytes32 _disputeEvidenceHash) external onlyBuyer inState(State.DeliverySignaled) {
        require(block.timestamp <= deliverySignaledAt + disputeWindow, "Escrow: dispute window expired");

        disputeEvidenceHash = _disputeEvidenceHash;
        currentState = State.Disputed;

        emit Disputed(buyer, _disputeEvidenceHash, block.timestamp);
    }

    /**
     * @dev Designated arbitrator resolves dispute.
     */
    function arbitrate(uint8 _decision, uint8 _sellerPct) external onlyArbitrator inState(State.Disputed) {
        require(_decision <= uint8(Ruling.Split), "Escrow: invalid ruling decision");

        uint256 balance = address(this).balance;
        require(balance > 0, "Escrow: no balance to arbitrate");

        if (_decision == uint8(Ruling.ReleaseToSeller)) {
            currentState = State.Released;
            emit Arbitrated(_decision, 100, balance, 0);
            _safeTransfer(seller, balance);
            emit FundsReleased(seller, balance);
        } else if (_decision == uint8(Ruling.RefundToBuyer)) {
            currentState = State.Refunded;
            emit Arbitrated(_decision, 0, 0, balance);
            _safeTransfer(buyer, balance);
            emit FundsRefunded(buyer, balance);
        } else {
            require(_sellerPct <= 100, "Escrow: invalid seller percentage");
            uint256 sellerAmount = (balance * _sellerPct) / 100;
            uint256 buyerAmount = balance - sellerAmount;

            currentState = _sellerPct >= 50 ? State.Released : State.Refunded;
            emit Arbitrated(_decision, _sellerPct, sellerAmount, buyerAmount);

            if (sellerAmount > 0) {
                _safeTransfer(seller, sellerAmount);
                emit FundsReleased(seller, sellerAmount);
            }
            if (buyerAmount > 0) {
                _safeTransfer(buyer, buyerAmount);
                emit FundsRefunded(buyer, buyerAmount);
            }
        }
    }

    /**
     * @dev Permissionless timeout check to prevent funds from locking indefinitely.
     */
    function checkTimeout() external {
        if (currentState == State.DeliverySignaled) {
            // If buyer fails to confirm or dispute within deliveryConfirmTimeout, auto-release to seller
            if (block.timestamp > deliverySignaledAt + deliveryConfirmTimeout) {
                currentState = State.Released;
                emit Confirmed(buyer, block.timestamp);
                _releaseFunds();
            }
        } else if (currentState == State.Funded) {
            // If seller fails to signal delivery within double timeout, buyer can claim refund
            if (block.timestamp > fundedAt + (deliveryConfirmTimeout * 2)) {
                currentState = State.Refunded;
                uint256 balance = address(this).balance;
                _safeTransfer(buyer, balance);
                emit FundsRefunded(buyer, balance);
            }
        } else {
            revert("Escrow: no timeout active for current state");
        }
    }

    function _releaseFunds() internal {
        currentState = State.Released;
        uint256 balance = address(this).balance;
        _safeTransfer(seller, balance);
        emit FundsReleased(seller, balance);
    }

    function _safeTransfer(address payable _to, uint256 _amount) internal {
        (bool success, ) = _to.call{value: _amount}("");
        require(success, "Escrow: transfer failed");
    }
}
