const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Escrow Smart Contract State Machine & Security", function () {
  let Escrow, escrow;
  let buyer, seller, arbitrator, stranger;
  let transcriptHash, evidenceHash, disputeEvidenceHash;
  const deliveryConfirmTimeout = 100; // 100 seconds
  const disputeWindow = 50; // 50 seconds

  beforeEach(async function () {
    [buyer, seller, arbitrator, stranger] = await ethers.getSigners();

    transcriptHash = ethers.id("canonical-transcript-hash-001");
    evidenceHash = ethers.id("seller-proof-of-delivery-001");
    disputeEvidenceHash = ethers.id("buyer-dispute-claim-001");

    Escrow = await ethers.getContractFactory("Escrow");
    escrow = await Escrow.connect(buyer).deploy(
      seller.address,
      arbitrator.address,
      transcriptHash,
      deliveryConfirmTimeout,
      disputeWindow
    );
    await escrow.waitForDeployment();
  });

  describe("Deployment & Initial State", function () {
    it("should initialize correct roles and Created state", async function () {
      expect(await escrow.buyer()).to.equal(buyer.address);
      expect(await escrow.seller()).to.equal(seller.address);
      expect(await escrow.arbitrator()).to.equal(arbitrator.address);
      expect(await escrow.transcriptHash()).to.equal(transcriptHash);
      expect(await escrow.currentState()).to.equal(0); // State.Created
    });

    it("should revert if buyer and seller are the same address", async function () {
      await expect(
        Escrow.connect(buyer).deploy(buyer.address, arbitrator.address, transcriptHash, 100, 50)
      ).to.be.revertedWith("Escrow: buyer and seller must differ");
    });
  });

  describe("Funding State Transition", function () {
    it("should allow buyer to fund contract", async function () {
      const fundAmount = ethers.parseEther("1.0");
      await expect(escrow.connect(buyer).fund({ value: fundAmount }))
        .to.emit(escrow, "Funded");

      expect(await escrow.currentState()).to.equal(1); // State.Funded
      expect(await escrow.amountLocked()).to.equal(fundAmount);
    });

    it("should revert if stranger or seller attempts funding", async function () {
      const fundAmount = ethers.parseEther("1.0");
      await expect(escrow.connect(seller).fund({ value: fundAmount }))
        .to.be.revertedWith("Escrow: only buyer allowed");
      await expect(escrow.connect(stranger).fund({ value: fundAmount }))
        .to.be.revertedWith("Escrow: only buyer allowed");
    });
  });

  describe("Delivery Signaling & Confirmation Path", function () {
    beforeEach(async function () {
      await escrow.connect(buyer).fund({ value: ethers.parseEther("1.0") });
    });

    it("should allow seller to signal delivery", async function () {
      await expect(escrow.connect(seller).signalDelivery(evidenceHash))
        .to.emit(escrow, "DeliverySignaled");

      expect(await escrow.currentState()).to.equal(2); // State.DeliverySignaled
      expect(await escrow.evidenceHash()).to.equal(evidenceHash);
    });

    it("should release funds upon buyer confirmation", async function () {
      await escrow.connect(seller).signalDelivery(evidenceHash);

      const sellerInitialBal = await ethers.provider.getBalance(seller.address);
      await expect(escrow.connect(buyer).confirmDelivery())
        .to.emit(escrow, "Confirmed")
        .to.emit(escrow, "FundsReleased");

      expect(await escrow.currentState()).to.equal(5); // State.Released
      const sellerFinalBal = await ethers.provider.getBalance(seller.address);
      expect(sellerFinalBal - sellerInitialBal).to.equal(ethers.parseEther("1.0"));
    });
  });

  describe("Dispute & Arbitration Flow", function () {
    beforeEach(async function () {
      await escrow.connect(buyer).fund({ value: ethers.parseEther("1.0") });
      await escrow.connect(seller).signalDelivery(evidenceHash);
    });

    it("should allow buyer to dispute within dispute window", async function () {
      await expect(escrow.connect(buyer).disputeDelivery(disputeEvidenceHash))
        .to.emit(escrow, "Disputed");

      expect(await escrow.currentState()).to.equal(4); // State.Disputed
    });

    it("should revert dispute call after dispute window expires", async function () {
      await ethers.provider.send("evm_increaseTime", [disputeWindow + 10]);
      await ethers.provider.send("evm_mine");

      await expect(escrow.connect(buyer).disputeDelivery(disputeEvidenceHash))
        .to.be.revertedWith("Escrow: dispute window expired");
    });

    it("should execute arbitrator Ruling.ReleaseToSeller correctly", async function () {
      await escrow.connect(buyer).disputeDelivery(disputeEvidenceHash);

      const sellerInitialBal = await ethers.provider.getBalance(seller.address);
      await expect(escrow.connect(arbitrator).arbitrate(0, 100)) // 0: ReleaseToSeller
        .to.emit(escrow, "Arbitrated")
        .withArgs(0, 100, ethers.parseEther("1.0"), 0);

      expect(await escrow.currentState()).to.equal(5); // State.Released
      const sellerFinalBal = await ethers.provider.getBalance(seller.address);
      expect(sellerFinalBal - sellerInitialBal).to.equal(ethers.parseEther("1.0"));
    });

    it("should execute arbitrator Ruling.RefundToBuyer correctly", async function () {
      await escrow.connect(buyer).disputeDelivery(disputeEvidenceHash);

      const buyerInitialBal = await ethers.provider.getBalance(buyer.address);
      await expect(escrow.connect(arbitrator).arbitrate(1, 0)) // 1: RefundToBuyer
        .to.emit(escrow, "Arbitrated")
        .withArgs(1, 0, 0, ethers.parseEther("1.0"));

      expect(await escrow.currentState()).to.equal(6); // State.Refunded
    });

    it("should execute arbitrator Ruling.Split correctly (60/40)", async function () {
      await escrow.connect(buyer).disputeDelivery(disputeEvidenceHash);

      const total = ethers.parseEther("1.0");
      const expectedSeller = ethers.parseEther("0.6");
      const expectedBuyer = ethers.parseEther("0.4");

      const sellerInitial = await ethers.provider.getBalance(seller.address);
      await expect(escrow.connect(arbitrator).arbitrate(2, 60)) // 2: Split 60%
        .to.emit(escrow, "Arbitrated")
        .withArgs(2, 60, expectedSeller, expectedBuyer);

      const sellerFinal = await ethers.provider.getBalance(seller.address);
      expect(sellerFinal - sellerInitial).to.equal(expectedSeller);
    });

    it("should revert if unauthorized party calls arbitrate()", async function () {
      await escrow.connect(buyer).disputeDelivery(disputeEvidenceHash);
      await expect(escrow.connect(buyer).arbitrate(0, 100))
        .to.be.revertedWith("Escrow: only arbitrator allowed");
      await expect(escrow.connect(seller).arbitrate(0, 100))
        .to.be.revertedWith("Escrow: only arbitrator allowed");
    });
  });

  describe("Permissionless Timeout Paths (No Stuck Funds)", function () {
    it("should auto-release to seller when delivery confirm timeout passes", async function () {
      await escrow.connect(buyer).fund({ value: ethers.parseEther("1.0") });
      await escrow.connect(seller).signalDelivery(evidenceHash);

      // Fast forward time past deliveryConfirmTimeout
      await ethers.provider.send("evm_increaseTime", [deliveryConfirmTimeout + 10]);
      await ethers.provider.send("evm_mine");

      const sellerInitialBal = await ethers.provider.getBalance(seller.address);

      // Anyone (even stranger) can call checkTimeout
      await expect(escrow.connect(stranger).checkTimeout())
        .to.emit(escrow, "Confirmed")
        .to.emit(escrow, "FundsReleased");

      expect(await escrow.currentState()).to.equal(5); // State.Released
      const sellerFinalBal = await ethers.provider.getBalance(seller.address);
      expect(sellerFinalBal - sellerInitialBal).to.equal(ethers.parseEther("1.0"));
    });

    it("should refund buyer if seller fails to signal delivery after extended timeout", async function () {
      await escrow.connect(buyer).fund({ value: ethers.parseEther("1.0") });

      // Fast forward time past double deliveryConfirmTimeout
      await ethers.provider.send("evm_increaseTime", [deliveryConfirmTimeout * 2 + 10]);
      await ethers.provider.send("evm_mine");

      await expect(escrow.connect(stranger).checkTimeout())
        .to.emit(escrow, "FundsRefunded");

      expect(await escrow.currentState()).to.equal(6); // State.Refunded
    });
  });
});
