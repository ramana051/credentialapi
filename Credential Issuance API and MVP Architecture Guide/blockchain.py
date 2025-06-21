"""
Blockchain integration utilities for credential verification.
"""

import hashlib
import json
import requests
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
import logging

from shared.config import settings

logger = logging.getLogger(__name__)


class BlockchainVerifier:
    """Handle blockchain-based credential verification."""
    
    def __init__(self):
        self.rpc_url = settings.polygon_rpc_url
        self.private_key = settings.polygon_private_key
        self.contract_address = settings.polygon_contract_address
        
        if self.rpc_url:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if self.private_key:
                self.account = Account.from_key(self.private_key)
        else:
            self.w3 = None
            self.account = None
    
    def anchor_credential_hash(self, credential_hash: str, credential_id: str) -> Optional[str]:
        """Anchor a credential hash to the blockchain."""
        
        if not self.w3 or not self.account:
            logger.warning("Blockchain not configured, skipping hash anchoring")
            return None
        
        try:
            # Simple contract ABI for storing hashes
            contract_abi = [
                {
                    "inputs": [
                        {"name": "credentialId", "type": "string"},
                        {"name": "credentialHash", "type": "string"}
                    ],
                    "name": "anchorCredential",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            
            if not self.contract_address:
                logger.warning("Contract address not configured")
                return None
            
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            # Build transaction
            transaction = contract.functions.anchorCredential(
                credential_id,
                credential_hash
            ).build_transaction({
                'from': self.account.address,
                'gas': 100000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"Credential hash anchored successfully: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                logger.error(f"Transaction failed: {tx_hash.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"Error anchoring credential hash: {e}")
            return None
    
    def verify_credential_hash(self, credential_hash: str, credential_id: str) -> Dict[str, Any]:
        """Verify a credential hash against the blockchain."""
        
        if not self.w3:
            return {
                "verified": False,
                "error": "Blockchain not configured"
            }
        
        try:
            # Contract ABI for reading hashes
            contract_abi = [
                {
                    "inputs": [{"name": "credentialId", "type": "string"}],
                    "name": "getCredentialHash",
                    "outputs": [{"name": "", "type": "string"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            if not self.contract_address:
                return {
                    "verified": False,
                    "error": "Contract address not configured"
                }
            
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            # Get stored hash from blockchain
            stored_hash = contract.functions.getCredentialHash(credential_id).call()
            
            # Compare hashes
            hash_match = stored_hash.lower() == credential_hash.lower()
            
            return {
                "verified": hash_match,
                "stored_hash": stored_hash,
                "provided_hash": credential_hash,
                "contract_address": self.contract_address,
                "network": "Polygon" if "polygon" in self.rpc_url.lower() else "Unknown"
            }
            
        except Exception as e:
            logger.error(f"Error verifying credential hash: {e}")
            return {
                "verified": False,
                "error": str(e)
            }
    
    def get_transaction_details(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get details of a blockchain transaction."""
        
        if not self.w3:
            return None
        
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            block = self.w3.eth.get_block(receipt.blockNumber)
            
            return {
                "transaction_hash": tx_hash,
                "block_number": receipt.blockNumber,
                "block_hash": receipt.blockHash.hex(),
                "timestamp": block.timestamp,
                "gas_used": receipt.gasUsed,
                "status": "success" if receipt.status == 1 else "failed",
                "from_address": tx["from"],
                "to_address": tx["to"]
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}")
            return None


def create_credential_hash(credential_data: Dict[str, Any]) -> str:
    """Create a deterministic hash of credential data."""
    
    # Extract key fields for hashing
    hash_data = {
        "credential_id": credential_data.get("credential_id"),
        "title": credential_data.get("title"),
        "recipient_name": credential_data.get("recipient_name"),
        "recipient_email": credential_data.get("recipient_email"),
        "issuer_id": credential_data.get("issuer_id"),
        "organization_id": credential_data.get("organization_id"),
        "issued_at": credential_data.get("issued_at"),
        "expires_at": credential_data.get("expires_at")
    }
    
    # Create deterministic JSON string
    json_string = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
    
    # Calculate SHA256 hash
    return hashlib.sha256(json_string.encode('utf-8')).hexdigest()


def verify_json_ld_signature(json_ld_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify JSON-LD digital signature (placeholder implementation)."""
    
    # This is a placeholder for JSON-LD signature verification
    # In a real implementation, you would:
    # 1. Extract the signature from the JSON-LD
    # 2. Verify the signature using the issuer's public key
    # 3. Check the signature algorithm and parameters
    
    try:
        # Check if signature exists
        if "proof" not in json_ld_data:
            return {
                "verified": False,
                "error": "No digital signature found"
            }
        
        proof = json_ld_data["proof"]
        
        # Basic validation of proof structure
        required_fields = ["type", "created", "verificationMethod", "proofValue"]
        missing_fields = [field for field in required_fields if field not in proof]
        
        if missing_fields:
            return {
                "verified": False,
                "error": f"Missing required proof fields: {missing_fields}"
            }
        
        # Placeholder verification (always returns true for demo)
        return {
            "verified": True,
            "signature_type": proof.get("type"),
            "created": proof.get("created"),
            "verification_method": proof.get("verificationMethod")
        }
        
    except Exception as e:
        return {
            "verified": False,
            "error": str(e)
        }


# Smart contract source code (Solidity) for reference
CREDENTIAL_REGISTRY_CONTRACT = """
pragma solidity ^0.8.0;

contract CredentialRegistry {
    mapping(string => string) private credentialHashes;
    mapping(string => address) private credentialIssuers;
    mapping(string => uint256) private credentialTimestamps;
    
    event CredentialAnchored(
        string indexed credentialId,
        string credentialHash,
        address indexed issuer,
        uint256 timestamp
    );
    
    function anchorCredential(
        string memory credentialId,
        string memory credentialHash
    ) public {
        require(bytes(credentialId).length > 0, "Credential ID cannot be empty");
        require(bytes(credentialHash).length > 0, "Credential hash cannot be empty");
        require(bytes(credentialHashes[credentialId]).length == 0, "Credential already anchored");
        
        credentialHashes[credentialId] = credentialHash;
        credentialIssuers[credentialId] = msg.sender;
        credentialTimestamps[credentialId] = block.timestamp;
        
        emit CredentialAnchored(credentialId, credentialHash, msg.sender, block.timestamp);
    }
    
    function getCredentialHash(string memory credentialId) public view returns (string memory) {
        return credentialHashes[credentialId];
    }
    
    function getCredentialIssuer(string memory credentialId) public view returns (address) {
        return credentialIssuers[credentialId];
    }
    
    function getCredentialTimestamp(string memory credentialId) public view returns (uint256) {
        return credentialTimestamps[credentialId];
    }
    
    function verifyCredential(
        string memory credentialId,
        string memory credentialHash
    ) public view returns (bool) {
        return keccak256(abi.encodePacked(credentialHashes[credentialId])) == 
               keccak256(abi.encodePacked(credentialHash));
    }
}
"""

