"""
Wallet Service with real balance fetching from Base Sepolia testnet
"""
import os
import json
from typing import Optional
from eth_account import Account
from web3 import Web3

WALLET_FILE = "wallet_data.json"

# Base Sepolia testnet RPC (using public Alchemy endpoint)
BASE_RPC = "https://base-sepolia.g.alchemy.com/v2/demo"

# USDC contract on Base Sepolia (test token - you may need to use a faucet)
# Note: This is a placeholder - real testnet USDC may have different address
USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # Base Sepolia USDC

# ERC20 ABI for balanceOf
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

# Enable HD wallet features
Account.enable_unaudited_hdwallet_features()

class WalletService:
    def __init__(self):
        self.account = None
        self.wallet_address = None
        self.web3 = None
        self._initialized = False
        self._balance_cache = {}
        self._cache_expiry = {}
    
    async def initialize(self):
        """Initialize wallet and web3 connection."""
        if self._initialized:
            return
        
        try:
            # Connect to Base
            self.web3 = Web3(Web3.HTTPProvider(BASE_RPC))
            if self.web3.is_connected():
                print(f"Connected to Base network")
            else:
                print("Warning: Could not connect to Base RPC")
            
            # Load or create wallet
            if os.path.exists(WALLET_FILE):
                with open(WALLET_FILE, 'r') as f:
                    data = json.load(f)
                    private_key = data.get('private_key')
                    self.account = Account.from_key(private_key)
                    self.wallet_address = self.account.address
                    print(f"Loaded wallet: {self.wallet_address}")
            else:
                self.account = Account.create()
                self.wallet_address = self.account.address
                self._save_wallet()
                print(f"Created new wallet: {self.wallet_address}")
                print(f"\n⚠️  Fund this wallet with USDC on Base to start trading!")
                print(f"   Address: {self.wallet_address}\n")
            
            self._initialized = True
            
        except Exception as e:
            print(f"Error initializing wallet: {e}")
            import traceback
            traceback.print_exc()
            self._initialized = True
    
    def _save_wallet(self):
        """Save wallet to file."""
        if self.account:
            with open(WALLET_FILE, 'w') as f:
                json.dump({
                    "address": self.wallet_address,
                    "private_key": self.account.key.hex()
                }, f)
            os.chmod(WALLET_FILE, 0o600)
    
    def get_address(self) -> Optional[str]:
        return self.wallet_address
    
    def get_private_key(self) -> Optional[str]:
        if self.account:
            return self.account.key.hex()
        return None
    
    async def get_balance(self, asset: str = "usdc") -> float:
        """Get real balance from Base network (with caching)."""
        if not self.wallet_address or not self.web3:
            return 0.0
        
        # Check cache (30 seconds TTL)
        import time
        now = time.time()
        if asset in self._cache_expiry and now < self._cache_expiry[asset]:
            return self._balance_cache[asset]
        
        try:
            if asset.lower() == "usdc":
                # Get USDC balance
                usdc_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(USDC_ADDRESS),
                    abi=ERC20_ABI
                )
                balance_wei = usdc_contract.functions.balanceOf(self.wallet_address).call()
                balance = balance_wei / 1e6
                
                # Update cache
                self._balance_cache[asset] = balance
                self._cache_expiry[asset] = now + 30  # Cache for 30s
                return balance
                
            elif asset.lower() == "eth":
                # Get ETH balance
                balance_wei = self.web3.eth.get_balance(self.wallet_address)
                balance = float(self.web3.from_wei(balance_wei, 'ether'))
                
                # Update cache
                self._balance_cache[asset] = balance
                self._cache_expiry[asset] = now + 30
                return balance
            else:
                return 0.0
        except Exception as e:
            print(f"Error getting {asset} balance: {e}")
            # Return cached value if available, even if expired
            return self._balance_cache.get(asset, 0.0)
    
    async def get_native_balance(self) -> float:
        """Get ETH balance."""
        return await self.get_balance("eth")
    
    def is_configured(self) -> bool:
        return self._initialized and self.wallet_address is not None


wallet_service = WalletService()
