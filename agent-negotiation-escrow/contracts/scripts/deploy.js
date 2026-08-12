const hre = require("hardhat");

async function main() {
  const [buyer, seller, arbitrator] = await hre.ethers.getSigners();

  const transcriptHash = hre.ethers.id("canonical-transcript-hash-example");
  const deliveryConfirmTimeout = 3600;
  const disputeWindow = 3600;

  console.log("Deploying Escrow contract with accounts:");
  console.log("  Buyer:", buyer.address);
  console.log("  Seller:", seller.address);
  console.log("  Arbitrator:", arbitrator.address);

  const Escrow = await hre.ethers.getContractFactory("Escrow");
  const escrow = await Escrow.deploy(
    seller.address,
    arbitrator.address,
    transcriptHash,
    deliveryConfirmTimeout,
    disputeWindow
  );

  await escrow.waitForDeployment();
  const address = await escrow.getAddress();

  console.log("Escrow contract deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
