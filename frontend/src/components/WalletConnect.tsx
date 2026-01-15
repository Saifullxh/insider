'use client';

import { useAccount, useConnect, useDisconnect, useConnectors } from 'wagmi';

export function WalletConnect() {
    const { address, isConnected } = useAccount();
    const { connect } = useConnect();
    const { disconnect } = useDisconnect();
    const connectors = useConnectors();

    if (isConnected && address) {
        return (
            <div className="flex items-center gap-4">
                <div className="px-4 py-2 bg-gray-800 rounded-lg">
                    <span className="text-sm text-gray-400">Connected:</span>
                    <span className="ml-2 font-mono text-white">
                        {address.slice(0, 6)}...{address.slice(-4)}
                    </span>
                </div>
                <button
                    onClick={() => disconnect()}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white font-semibold transition"
                >
                    Disconnect
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-3">
            {connectors.map((connector) => (
                <button
                    key={connector.uid}
                    onClick={() => connect({ connector })}
                    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition flex items-center justify-center gap-2"
                >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                    </svg>
                    Sign in with Passkey
                </button>
            ))}
        </div>
    );
}
