import { http, createConfig } from 'wagmi';
import { baseSepolia } from 'wagmi/chains';
import { coinbaseWallet } from 'wagmi/connectors';

export const config = createConfig({
    chains: [baseSepolia],
    connectors: [
        coinbaseWallet({
            appName: 'Polymarket AI',
            preference: 'smartWalletOnly', // Force Smart Wallet for better UX
        }),
    ],
    transports: {
        [baseSepolia.id]: http(),
    },
});
